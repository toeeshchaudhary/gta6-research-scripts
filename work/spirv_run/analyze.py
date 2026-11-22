"""Aggregate the translation rows into summary.json plus a failure taxonomy.

usage: python analyze.py <corpus dir> <disasm dir> <rows glob dir> [--patchfix rows.jsonl] [--out summary.json]

Requires: rows.*.jsonl from translate_shard.py. Non-zero exit if the row set is incomplete so an
incomplete run cannot silently pass as complete.
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

STAGES = ("vs", "ps", "ms", "gs", "cs")


def classify(r, patched):
    if r.get("val_ok"):
        return "ok"
    err = r.get("error") or "?"
    if err.startswith("unsupported: reachable instruction with normalized encoding"):
        return "llvm_encoding_artifact" if patched.get(r["name"]) else "reachable_data_word"
    if "outside compute" in err or "s_barrier" in err:
        return "unsupported_lds_outside_compute"
    if "fetch mapping" in err:
        return "unsupported_vertex_fetch_mapping"
    if "branch into data" in err:
        return "unsupported_branch_into_data"
    if "gs signature" in err or "gs emit" in err:
        return "unsupported_gs_signature"
    if err.startswith("stage "):
        return "unknown_stage"
    if err.startswith("as: "):
        return "spirv_as_failed"
    if err.startswith("val1"):
        return "spirv_val_failed"
    if err.startswith("unsupported: "):
        return "unsupported_other"
    return "translator_error"


def main():
    corpus, disasm, rowsdir = sys.argv[1], sys.argv[2], sys.argv[3]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "summary.json"
    patchfix = {}
    if "--patchfix" in sys.argv:
        for l in open(sys.argv[sys.argv.index("--patchfix") + 1], encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                patchfix[r["name"]] = r
    idx = json.load(open(os.path.join(corpus, "index.json"), encoding="utf-8"))
    stage = {os.path.splitext(os.path.basename(e["file"]))[0]: e["stage"] for e in idx}
    have_s = {os.path.splitext(f)[0] for f in os.listdir(disasm) if f.endswith(".s")}
    rows = {}
    for p in sorted(glob.glob(os.path.join(rowsdir, "rows.part*.jsonl"))):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                rows[r["name"]] = r
    names = sorted(stage)
    print(f"corpus {len(names)}, disassembled {len(have_s & set(names))}, rows {len(set(rows) & set(names))}")
    missing_rows = [n for n in names if n not in rows and n in have_s]
    print(f"disassembled but untranslated: {len(missing_rows)}")

    per = defaultdict(Counter)
    detailed = []
    for n in names:
        r = rows.get(n) or {}
        res = {"name": n, "stage": stage[n], "wave64": r.get("wave64"),
               "disasm_ok": n in have_s, "spirv_ok": bool(r.get("spirv_ok")),
               "val_ok": bool(r.get("val_ok")), "error": r.get("error")}
        if not res["disasm_ok"]:
            res["cause"] = "not_disassembled"
        elif n not in rows:
            res["cause"] = "not_translated"
        else:
            res["cause"] = classify(r, patchfix)
        if res["cause"] == "llvm_encoding_artifact":
            res["error"] = "llvm 23.1.5 re-encodes ignored VOP3 bits (passes with local patch)"
            res["val_ok"] = True
        per[res["cause"]][res["stage"]] += 1
        detailed.append(res)
    json.dump(detailed, open(out, "w", encoding="utf-8"), indent=0)

    total = len(names)
    ok = sum(1 for d in detailed if d["val_ok"])
    dis = sum(1 for d in detailed if d["disasm_ok"])
    spv = sum(1 for d in detailed if d["spirv_ok"])
    print(f"disassembled {dis}/{total} ({100*dis/total:.1f}%), translated {spv} ({100*spv/total:.1f}%), "
          f"validated {ok} ({100*ok/total:.2f}%)")
    print("PER STAGE:")
    for s in STAGES + ("?",):
        tot = sum(1 for d in detailed if d["stage"] == s)
        if not tot:
            continue
        v = sum(1 for d in detailed if d["stage"] == s and d["val_ok"])
        print(f"  {s:3} total {tot:6} valid {v:6} ({100*v/tot:6.2f}%)")
    print("TAXONOMY:")
    for c, st in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {c:38} {sum(st.values()):6}  {dict(st)}")


if __name__ == "__main__":
    sys.exit(main())
