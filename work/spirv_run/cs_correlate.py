"""Correlate compute-shader translation outcome with the COMPUTE_PGM_RSRC2 metadata in each FSSM header.

Tests the design.md prediction that CS failures are a *metadata* problem (per-shader user-SGPR count /
TG_SIZE_EN), not a code problem.

usage: python cs_correlate.py <corpus dir> <rows jsonl glob dir>
"""
import glob
import json
import os
import struct
import sys
from collections import Counter, defaultdict


def main():
    corpus, rowsdir = sys.argv[1], sys.argv[2]
    idx = json.load(open(os.path.join(corpus, "index.json"), encoding="utf-8"))
    cs = [os.path.splitext(e["file"])[0] for e in idx if e["stage"] == "cs"]
    rows = {}
    for p in glob.glob(os.path.join(rowsdir, "rows.part*.jsonl")):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                if r["stage"] == "cs":
                    rows[r["name"]] = r
    print(f"cs in corpus {len(cs)}, cs rows {len(rows)}")
    by_cause = defaultdict(lambda: {"n": 0, "tgsize": 0, "user": Counter(), "tgid": Counter(),
                                    "maxoff": 0, "lds": Counter()})
    for n in cs:
        r = rows.get(n)
        if not r:
            cause = "not_run"
        elif r["val_ok"]:
            cause = "ok"
        elif r["spirv_ok"]:
            cause = "spirv_emitted_but_invalid"
        else:
            cause = (r.get("error") or "?")[:60]
        hdr = open(os.path.join(corpus, "fssm", n + ".fssm"), "rb").read(0x148)
        rsrc2, lx, ly, lz = struct.unpack_from("<4I", hdr, 0x138)
        b = by_cause[cause]
        b["n"] += 1
        b["tgsize"] += (rsrc2 >> 10) & 1
        b["user"][(rsrc2 >> 1) & 31] += 1
        b["tgid"][(rsrc2 >> 7) & 7] += 1
        b["lds"][(rsrc2 >> 15) & 0x1FF] += 1
        b["maxoff"] = max(b["maxoff"], lx * ly * lz)
    print(f"{'cause':40}{'n':>7}{'tgsize_en':>11}{'user_sgpr (median-ish spread)':>32}")
    for c, b in sorted(by_cause.items(), key=lambda kv: -kv[1]["n"]):
        us = sorted(b["user"].items())
        spread = f"{us[0][0]}..{us[-1][0]}" if us else "-"
        print(f"{c:40}{b['n']:7}{b['tgsize']:11}{spread:>32}")
        print(f"{'':40}  user_sgpr histogram: {dict(b['user'].most_common(6))}")
        print(f"{'':40}  tgid_enable bits: {dict(b['tgid'].most_common(4))}  max group size {b['maxoff']}")


if __name__ == "__main__":
    sys.exit(main())
