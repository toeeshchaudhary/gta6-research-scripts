"""Quantify the compute-stage failure taxonomy for the report.

Joins three sources:
  * translation/validation rows (logs_cs/*.jsonl)
  * disassembly result rows (logs_cs/rows_disasm.jsonl)
  * per-blob COMPUTE_PGM_RSRC2 metadata (USER_SGPR count, TG_SIZE_EN)
and reports how cs failures cluster, so the "compute fails for the documented missing user-SGPR
count from the game executable" claim is measured rather than asserted.

usage: python analyze_cs.py <todo list> <out json>
"""
import glob
import json
import os
import re
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRCS = ["cs_fssm", "cs_missing_fssm", "cs_missing2"]
DISASM = os.path.join(HERE, "cs_in", "disasm")


def blob(n):
    for s in SRCS:
        p = os.path.join(HERE, s, n + ".fssm")
        if os.path.exists(p):
            return p
    return None


def rsrc2_fields(n):
    p = blob(n)
    if not p:
        return None
    hdr = open(p, "rb").read(0x148)
    if len(hdr) < 0x140:
        return None
    (rsrc2,) = struct.unpack_from("<I", hdr, 0x138)
    return {"user_sgpr": (rsrc2 >> 1) & 31, "tg_size_en": (rsrc2 >> 10) & 1,
            "tgid_en": (rsrc2 >> 7) & 7, "lds": (rsrc2 >> 15) & 0x1FF}


# a compute shader that consumes user SGPRs reads s0.. onward in its preamble
USER_RE = re.compile(r"\bs\[(\d+):|, s(\d+)(?:,|$)|s(\d+)\b")


def text_user_sgpr(n):
    """Largest low SGPR index the shader actually reads (a proxy for user-SGPR consumption)."""
    p = os.path.join(DISASM, n + ".s")
    if not os.path.exists(p):
        return None
    hi = -1
    with open(p, encoding="utf-8", errors="replace") as f:
        f.readline()
        for ln in f:
            if ln.startswith("; ---"):
                break
            if not ln[:1] == "\t":
                continue
            for m in USER_RE.finditer(ln):
                for g in m.groups():
                    if g:
                        hi = max(hi, int(g))
    return hi


def main():
    todo = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    out_p = sys.argv[2]

    disasm_rows = {}
    dp = os.path.join(HERE, "logs_cs", "rows_disasm.jsonl")
    if os.path.exists(dp):
        for l in open(dp, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                disasm_rows[r["name"]] = r

    trans = {}
    for p in glob.glob(os.path.join(HERE, "logs_cs", "rows.*.jsonl")):
        if os.path.basename(p) == "rows_disasm.jsonl":
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                trans[(r.get("name") or "").lstrip("\ufeff")] = r

    stage = Counter()
    errors = Counter()
    per = []
    for n in todo:
        d = disasm_rows.get(n)
        s_path = os.path.join(DISASM, n + ".s")
        has_s = os.path.exists(s_path)
        if not has_s:
            st = "disasm:no .s produced"
        elif d and d.get("result") == "no s_endpgm":
            st = "disasm:no s_endpgm"
        elif d and d.get("result") == "scan failed":
            st = "disasm:scan failed"
        elif d and d.get("result") == "invalid words":
            st = "disasm:invalid words (partial decode)"
        else:
            t = trans.get(n)
            if t is None:
                st = "not translated"
            elif not t.get("spirv_ok"):
                st = "translation failed"
            elif not t.get("as_ok"):
                st = "spirv-as failed"
            elif not t.get("val_ok"):
                st = "spirv-val 1.2 rejected"
            elif not t.get("val13_ok"):
                st = "spirv-val 1.3 rejected"
            else:
                st = "ok"
        stage[st] += 1
        t = trans.get(n) or {}
        if t.get("error"):
            e = re.sub(r"^(unsupported: )?(Unsupported|UnsupportedInstruction): ", r"\1", t["error"])
            errors[e[:110]] += 1
        f = rsrc2_fields(n)
        per.append({"name": n, "stage": st, "err": t.get("error"),
                    "insns": t.get("insns"),
                    "user_sgpr": f["user_sgpr"] if f else None,
                    "tg_size_en": f["tg_size_en"] if f else None,
                    "user_read_hi": text_user_sgpr(n)})

    def cluster(pred, label):
        sel = [p for p in per if pred(p)]
        fails = [p for p in sel if p["stage"] != "ok"]
        return {"label": label, "n": len(sel), "fail": len(fails),
                "fail_pct": round(100.0 * len(fails) / len(sel), 1) if sel else None}

    clusters = [
        cluster(lambda p: (p["user_sgpr"] or 0) > 0, "header declares USER_SGPR > 0"),
        cluster(lambda p: (p["user_sgpr"] or 0) == 0, "header declares USER_SGPR == 0"),
        cluster(lambda p: p["tg_size_en"] == 1, "TG_SIZE_EN set"),
        cluster(lambda p: (p["user_read_hi"] or -1) >= 0, "code reads s0.. from user SGPRs"),
        cluster(lambda p: (p["user_read_hi"] or -1) < 0, "code reads no low SGPR"),
        cluster(lambda p: p["stage"].startswith("disasm"), "fails at disassembly"),
        cluster(lambda p: p["stage"] == "translation failed", "fails at translation"),
        cluster(lambda p: "val" in p["stage"], "fails at validation"),
    ]
    res = {"n": len(todo), "stage": dict(stage.most_common()),
           "top_errors": dict(errors.most_common(25)),
           "clusters": clusters,
           "user_sgpr_hist_overall": dict(Counter(p["user_sgpr"] for p in per).most_common()),
           "user_sgpr_hist_failing": dict(Counter(p["user_sgpr"] for p in per
                                                 if p["stage"] != "ok").most_common())}
    json.dump(res, open(out_p, "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: res[k] for k in ("n", "stage", "clusters")}, indent=1))
    print("top_errors:")
    for e, c in list(errors.most_common(12)):
        print(f"  {c:5} {e}")


if __name__ == "__main__":
    sys.exit(main())
