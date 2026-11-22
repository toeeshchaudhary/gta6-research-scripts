"""Quality checks on the scan shards: hash plausibility, position coherence, per-class mix.

usage: python -I quality.py <outdir> <sample_rows> <report_json>
"""
import glob
import json
import math
import random
import sys

outdir, nsample, report_json = sys.argv[1], int(sys.argv[2]), sys.argv[3]
shards = sorted(glob.glob(outdir + "/inst_*.tsv"))
rows = []
total = 0
for sh in shards:
    with open(sh, encoding="ascii", errors="replace") as f:
        for line in f:
            total += 1
            if len(rows) < nsample * 4 and random.random() < 0.05:
                rows.append(line.rstrip("\n").split("\t"))
random.shuffle(rows)

floaty = small = zero = 0
cls = {"M": 0, "P": 0, "S": 0}
byres = {}
for p in rows:
    if len(p) < 13:
        continue
    h = int(p[1], 16)
    if 0x3C000000 <= h < 0x42000000:
        floaty += 1
    if h < 0x01000000:
        small += 1
    if h == 0:
        zero += 1
    cls[p[12]] = cls.get(p[12], 0) + 1
    byres.setdefault(p[0], []).append((float(p[2]), float(p[3]), float(p[4])))

n = sum(cls.values()) or 1
coh_all = []
for res, pts in list(byres.items()):
    if len(pts) < 20:
        continue
    close = 0
    for a, b in zip(pts, pts[1:]):
        d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
        if d < 40000:
            close += 1
    coh_all.append(close / (len(pts) - 1))
coh_all.sort()

zs = sorted(abs(p[2]) for pts in byres.values() for p in pts)
rep = {
    "shards": len(shards), "rows_seen": total, "rows_sampled": n,
    "float_bit_pattern_hashes": floaty / n, "hash_below_0x01000000": small / n,
    "hash_zero": zero / n, "class_mix": {k: v / n for k, v in cls.items()},
    "resources_sampled": len(byres),
    "coherence_median": coh_all[len(coh_all) // 2] if coh_all else None,
    "coherence_p10": coh_all[len(coh_all) // 10] if coh_all else None,
    "z_abs_median": zs[len(zs) // 2] if zs else None,
    "z_abs_p99": zs[int(len(zs) * 0.99)] if zs else None,
}
json.dump(rep, open(report_json, "w"), indent=1)
print(json.dumps(rep, indent=1))
