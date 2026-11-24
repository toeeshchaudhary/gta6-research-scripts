"""Finalise the complete-data scene: add per-row yaw + strict verdict, then report stats.

Writes scene_world_complete.json (schema of the world2 scene plus `class` (as requested), `yaw`,
`strict`) and a stats report with the corrected (strict) extent, census, bind rate and float shares.

usage: python -I finalbuild.py <scene.json> <strict.tsv> <names.tsv> <arch_model.json> <stats.json>
"""
import collections
import json
import struct
import sys

scene, strict_tsv, names_tsv, arch_model, stats_json = sys.argv[1:6]

inst = json.load(open(scene, encoding="utf-8"))["instances"]
print(f"scene rows {len(inst):,}")

verdict = {}
for line in open(strict_tsv, encoding="ascii"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 7:
        continue
    verdict[(p[0], round(float(p[2]), 3), round(float(p[3]), 3), round(float(p[4]), 3))] = (float(p[5]), int(p[6]))

names = {}
for line in open(names_tsv, encoding="utf-8", errors="replace"):
    p = line.split("\t")
    if len(p) >= 2 and p[0].startswith("0x"):
        names[p[0].lower()] = p[1]

bind = {b["archetype_hash"].lower() for b in json.load(open(arch_model, encoding="utf-8"))["bindings"]}

st = collections.Counter()
matched = 0
with open(scene, "w", encoding="utf-8") as out:
    out.write('{"note":"complete-data levels.rpf scan (508,767/508,767 candidates). class M = '
              'joaat-verified local interior/MLO child, P = unnamed repeated-hash array, S = world-space '
              '0DRP placement. yaw = float at +0x0C of the record; strict = 1 when the record passes the '
              'yaw-range + non-float-hash test, i.e. when it is a genuine placement record",')
    out.write('"instances":[')
    first = True
    for r in inst:
        key = (r["resource"], round(r["pos"][0], 3), round(r["pos"][1], 3), round(r["pos"][2], 3))
        v = verdict.get(key)
        if r.get("class") == "S":
            if v is None:
                st["s_unmatched"] += 1
                r["yaw"] = None
                r["strict"] = None
            else:
                matched += 1
                r["yaw"] = round(v[0], 6)
                r["strict"] = v[1]
                st["s_genuine" if v[1] else "s_misread"] += 1
        else:
            r["yaw"] = None
            r["strict"] = None
        if not first:
            out.write(",")
        first = False
        out.write(json.dumps(r, separators=(",", ":")))
    out.write("]}")


def pct(a, q):
    b = sorted(a)
    return b[min(len(b) - 1, int(q * (len(b) - 1)))] if b else 0.0


rep = {"rows": len(inst), "matched_s": matched}
for tag, sel in (("all_s", lambda r: r.get("class") == "S"),
                 ("genuine_s", lambda r: r.get("class") == "S" and r.get("strict") == 1),
                 ("misread_s", lambda r: r.get("class") == "S" and r.get("strict") == 0)):
    rows = [r for r in inst if sel(r)]
    xs = [r["pos"][0] for r in rows]
    ys = [r["pos"][1] for r in rows]
    zs = [r["pos"][2] for r in rows]
    h = collections.Counter(r["hash"].lower() for r in rows)


    def cff(v):
        f = struct.unpack("<f", struct.pack("<I", int(v, 16)))[0]
        return f == f and 0.01 <= abs(f) <= 20000.0


    rep[tag] = {
        "instances": len(rows),
        "resources": len({r["resource"] for r in rows}),
        "x": {"p02": round(pct(xs, .02), 1), "p50": round(pct(xs, .5), 1), "p98": round(pct(xs, .98), 1),
              "min": round(min(xs), 1) if xs else 0, "max": round(max(xs), 1) if xs else 0},
        "y": {"p02": round(pct(ys, .02), 1), "p50": round(pct(ys, .5), 1), "p98": round(pct(ys, .98), 1),
              "min": round(min(ys), 1) if ys else 0, "max": round(max(ys), 1) if ys else 0},
        "z": {"p02": round(pct(zs, .02), 1), "p50": round(pct(zs, .5), 1), "p98": round(pct(zs, .98), 1),
              "min": round(min(zs), 1) if zs else 0, "max": round(max(zs), 1) if zs else 0},
        "distinct_hashes": len(h),
        "coord_float_distinct": sum(1 for k in h if cff(k)),
        "coord_float_distinct_frac": round(sum(1 for k in h if cff(k)) / len(h), 4) if h else 0,
        "named_distinct": sum(1 for k in h if k in names),
        "bound_instances": sum(n for k, n in h.items() if k in bind),
        "bind_rate": round(sum(n for k, n in h.items() if k in bind) / len(rows), 6) if rows else 0,
        "top20": [{"hash": k, "instances": n, "name": names.get(k),
                   "as_float": round(struct.unpack("<f", struct.pack("<I", int(k, 16)))[0], 4)
                   if struct.unpack("<f", struct.pack("<I", int(k, 16)))[0] == struct.unpack("<f", struct.pack("<I", int(k, 16)))[0] else None}
                  for k, n in h.most_common(20)],
    }

rep["hash_zero_rows"] = sum(1 for r in inst if r["hash"] == "0x00000000")
json.dump(rep, open(stats_json, "w", encoding="utf-8"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=1)[:6000])
