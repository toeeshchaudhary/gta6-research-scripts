"""Inter-resource tiling check: quantise sampled positions to 1 m cubes and count how many cubes
are claimed by more than one resource. If resources tile a global map this stays near zero.

usage: python -I tilecheck.py <outdir> <max_rows> <report_json>
"""
import glob
import json
import random
import sys

outdir, limit, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
shards = sorted(glob.glob(outdir + "/inst_*.tsv"))
cubes = {}
seen = 0
random.seed(7)
for sh in shards:
    with open(sh, encoding="ascii", errors="replace") as f:
        for line in f:
            if seen >= limit:
                break
            seen += 1
            p = line.split("\t")
            if len(p) < 13:
                continue
            x, y, z = float(p[2]), float(p[3]), float(p[4])
            k = (int(x // 1), int(y // 1), int(z // 1))
            s = cubes.get(k)
            if s is None:
                cubes[k] = {p[0]}
            else:
                s.add(p[0])
    if seen >= limit:
        break

shared = sum(1 for v in cubes.values() if len(v) > 1)
# 100 m cell occupancy for the neighbour falloff
cells = {}
for (x, y, z) in list(cubes.keys()):
    k = (x // 100, y // 100)
    cells[k] = cells.get(k, 0) + 1
hist = {}
for v in cells.values():
    hist[v] = hist.get(v, 0) + 1
rep = {"rows": seen, "occupied_1m_cubes": len(cubes), "shared_cubes": shared,
       "shared_fraction": shared / len(cubes) if cubes else 0,
       "occupied_100m_cells": len(cells),
       "cell_occupancy_hist": dict(sorted(hist.items())[:6])}
json.dump(rep, open(out, "w"), indent=1)
print(json.dumps(rep, indent=1))
