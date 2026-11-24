"""Repair rows: shaders that already have a .spv but no JSON row (produced before the row logs existed).

Re-disassembles the blob (for insns + the user-SGPR taxonomy) and re-validates the existing .spv, emitting a
row in the standard schema plus a taxonomy row, without re-translating.

usage: python repair_orphans.py [--rows logs_cs/rows.orphan.jsonl] [--tax logs_cs/tax.orphan.jsonl]
"""
import argparse
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cs_shard as S  # noqa: E402
import translate_shard as TS  # noqa: E402

SPIRV = os.path.join(HERE, "..", "spirv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=os.path.join(HERE, "logs_cs", "rows.orphan.jsonl"))
    ap.add_argument("--tax", default=os.path.join(HERE, "logs_cs", "tax.orphan.jsonl"))
    ap.add_argument("--mcpu", default="gfx1013")
    ap.add_argument("--only-orphans", action="store_true", default=True)
    a = ap.parse_args()

    have_row = set()
    for f in glob.glob(os.path.join(HERE, "logs_*", "rows*.jsonl")) + glob.glob(
            os.path.join(HERE, "logs_cs", "rows*.jsonl")):
        for l in open(f, encoding="utf-8", errors="replace"):
            l = l.strip()
            if not l:
                continue
            try:
                have_row.add(json.loads(l)["name"])
            except Exception:  # noqa: BLE001
                pass
    spv = [os.path.splitext(f)[0] for f in os.listdir(os.path.join(HERE, "cs_spirv"))
           if f.endswith(".spv")]
    todo = sorted(set(spv) - have_row)
    print("orphan .spv without row: %d" % len(todo), flush=True)
    valbin = os.path.join(SPIRV, "spirv-val.exe")
    nval = nval13 = 0
    with open(a.rows, "a", encoding="utf-8") as rows, open(a.tax, "a", encoding="utf-8") as tax:
        for i, name in enumerate(todo):
            row = {"name": name, "stage": "cs", "insns": 0, "spirv_ok": True, "as_ok": True,
                   "val_ok": False, "val13_ok": False, "wave64": None, "error": None}
            t = {"name": name, "kind": "translated", "early_slots": [], "insns": 0, "repaired": True}
            spath = os.path.join(S.ASMDIR, name + ".s")
            try:
                r = S.D.one(os.path.join(S.FSSM, name + ".fssm"), S.ASMDIR, a.mcpu)
            except Exception as e:  # noqa: BLE001
                r = "exc:" + type(e).__name__
            t["disasm"] = r
            if os.path.exists(spath):
                txt = open(spath, encoding="utf-8", errors="replace").read()
                row["insns"] = TS.n_insns(spath)
                early, n_insn = S.sgpr_reads(txt)
                t["insns"] = n_insn
                t["early_slots"] = sorted({s for _, s, _ in early})
                t["early_n"] = len(early)
                t["early_first"] = [x[2][:100] for x in early[:3]]
                t["uses_load"] = "s_load_" in txt
                os.remove(spath)
            sv = os.path.join(HERE, "cs_spirv", name + ".spv")
            rc, err = TS.run([valbin, "--target-env", "vulkan1.2",
                              "--allow-offset-texture-operand", sv])
            if rc == 0:
                row["val_ok"] = True
                nval += 1
            else:
                row["error"] = "val1.2: " + (err.splitlines() or ["rc=%d" % rc])[0][:200]
                t["kind"] = "val12"
            rc3, err3 = TS.run([valbin, "--target-env", "vulkan1.3",
                                "--allow-offset-texture-operand", sv])
            if rc3 == 0:
                row["val13_ok"] = True
                nval13 += 1
            elif row["val_ok"]:
                row["error"] = "val1.3: " + (err3.splitlines() or ["rc=%d" % rc3])[0][:200]
            rows.write(json.dumps(row) + "\n"); rows.flush()
            tax.write(json.dumps(t) + "\n"); tax.flush()
            if (i + 1) % 25 == 0:
                print("  %d/%d val=%d" % (i + 1, len(todo), nval), flush=True)
    print("DONE repairs %d: val=%d val13=%d" % (len(todo), nval, nval13), flush=True)


if __name__ == "__main__":
    sys.exit(main())
