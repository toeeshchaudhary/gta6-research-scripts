"""Validate already-emitted .spvasm/.spv files that have no row, instead of retranslating them.

usage: python validate_orphans.py <corpus dir> <disasm dir> <spirv dir> <names file> <rows out>
Appends one row per name in the same schema as translate_shard.py.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SPIRV = os.path.join(HERE, "..", "spirv")


def n_insns(path):
    if not os.path.exists(path):
        return 0
    n = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        f.readline()
        for ln in f:
            if ln.startswith("; ---"):
                break
            if ln[:1] == "\t":
                n += 1
    return n


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stderr or "").strip()


def main():
    corpus, disasm, spirv, namesf, rowsf = sys.argv[1:6]
    idx = json.load(open(os.path.join(corpus, "index.json"), encoding="utf-8"))
    stage = {os.path.splitext(e["file"])[0]: e["stage"] for e in idx}
    names = [l.strip() for l in open(namesf, encoding="utf-8") if l.strip()]
    valbin = os.path.join(SPIRV, "spirv-val.exe")
    asbin = os.path.join(SPIRV, "spirv-as.exe")
    ok12 = ok13 = 0
    t0 = time.time()
    with open(rowsf, "a", encoding="utf-8") as out:
        for n in names:
            row = {"name": n, "stage": stage.get(n, "?"),
                   "insns": n_insns(os.path.join(disasm, n + ".s")),
                   "spirv_ok": True, "as_ok": False, "val_ok": False, "val13_ok": False,
                   "wave64": None, "error": None}
            spv = os.path.join(spirv, n + ".spv")
            asm = os.path.join(spirv, n + ".spvasm")
            if not os.path.exists(spv):
                rc, err = run([asbin, asm, "-o", spv, "--target-env", "vulkan1.2"])
                if rc != 0:
                    row["error"] = "as: " + (err.splitlines() or ["?"])[0][:160]
                    out.write(json.dumps(row) + "\n")
                    continue
            row["as_ok"] = True
            rc2, err2 = run([valbin, "--target-env", "vulkan1.2",
                             "--allow-offset-texture-operand", spv])
            rc3, err3 = run([valbin, "--target-env", "vulkan1.3",
                             "--allow-offset-texture-operand", spv])
            if rc2 == 0:
                row["val_ok"] = True
                ok12 += 1
            if rc3 == 0:
                row["val13_ok"] = True
                ok13 += 1
            if rc2 != 0:
                row["error"] = "val1.2: " + (err2.splitlines() or ["?"])[0][:160]
            elif rc3 != 0:
                row["error"] = "val1.3: " + (err3.splitlines() or ["?"])[0][:160]
            out.write(json.dumps(row) + "\n")
    print(f"orphans validated {len(names)}: val1.2={ok12} val1.3={ok13} in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
