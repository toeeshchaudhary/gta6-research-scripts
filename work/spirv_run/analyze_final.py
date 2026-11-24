"""Final aggregate over every row file on disk: per-stage attempted / disassembled / translated / validated,
failure taxonomy, and the compute correlation hook.

Rows are merged latest-file-wins by file mtime, so a recovery row overrides an older row for the same name.

usage: python analyze_final.py <corpus dir> [--out summary_final.json]
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
STAGES = ("vs", "ps", "ms", "gs", "cs")


def classify(r):
    if r.get("val_ok"):
        return "ok"
    if r.get("val13_ok") and not r.get("val_ok"):
        return "ok_v13_only"
    err = r.get("error") or "?"
    if "reachable instruction with normalized encoding" in err:
        return "reachable_data_word"
    if "outside compute" in err or "s_barrier" in err:
        return "unsupported_lds_outside_compute"
    if "fetch mapping" in err:
        return "unsupported_vertex_fetch_mapping"
    if "branch into data" in err:
        return "unsupported_branch_into_data"
    if "gs signature" in err or "gs emit" in err:
        return "unsupported_gs_signature"
    if "gs sendmsg" in err:
        return "unsupported_gs_sendmsg"
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
    corpus = sys.argv[1]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "summary_final.json"
    idx = json.load(open(os.path.join(corpus, "index.json"), encoding="utf-8"))
    stage = {os.path.splitext(e["file"])[0]: e["stage"] for e in idx}
    rows = {}
    files = sorted(glob.glob(os.path.join(HERE, "logs*", "*rows*.jsonl")), key=os.path.getmtime)
    for p in files:
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                if r["name"] in stage:      # ignore names outside the reference corpus
                    rows[r["name"]] = r
    dis = set()
    for d in (os.path.join(HERE, "s2_in", "disasm"), os.path.join(HERE, "cs_in", "disasm")):
        if os.path.isdir(d):
            dis |= {os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".s")}
    print(f"rows files {len(files)}, unique rows in corpus {len(rows)}, disassembled {len(dis & set(rows))}")

    per = defaultdict(Counter)
    stats = defaultdict(Counter)
    detail = []
    for n, st in stage.items():
        r = rows.get(n)
        s = stats[st]
        s["corpus"] += 1
        if n in dis:
            s["disassembled"] += 1
        if r:
            s["translated"] += 1 if r.get("spirv_ok") else 0
            s["attempted"] += 1
            if r.get("as_ok"):
                s["assembled"] += 1
            if r.get("val_ok"):
                s["validated"] += 1
            if r.get("val13_ok"):
                s["validated13"] += 1
            if r.get("wave64"):
                s["wave64"] += 1
            cause = classify(r)
        else:
            cause = "not_disassembled" if n not in dis else "not_translated"
        per[cause][st] += 1
        detail.append({"name": n, "stage": st, "cause": cause, "error": (r or {}).get("error"),
                       "insns": (r or {}).get("insns")})
    json.dump(detail, open(out, "w", encoding="utf-8"), indent=0)

    print(f"{'stage':6}{'corpus':>8}{'disasm':>8}{'attempted':>11}{'translated':>12}{'val1.2':>9}{'val1.3':>9}{'wave64':>8}")
    for st in STAGES:
        s = stats[st]
        c = s["corpus"]
        if not c:
            continue
        print(f"{st:6}{c:8}{s['disassembled']:8}{s['attempted']:11}{s['translated']:12}"
              f"{s['validated']:9}{s['validated13']:9}{s['wave64']:8}   "
              f"({100*s['validated']/c:.1f}% of stage)")
    tot = sum(len([1 for n in stage if n in dis]), 0)
    print(f"TOTAL corpus {len(stage)}, disassembled {tot}")
    print("TAXONOMY:")
    for c, st in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {c:32}{sum(st.values()):7}  {dict(sorted(st.items()))}")


if __name__ == "__main__":
    sys.exit(main())
