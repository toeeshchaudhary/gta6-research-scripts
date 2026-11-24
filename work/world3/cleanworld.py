"""Final clean-world subset: strict records that are actually in the world (away from the local origin).

Class-S records that sit within a few metres of the origin are local child tables (class M read with
the S frame), not world placement; 41 % of the "strict" rows are that. A record is world placement
here when strict=1 and max(|x|,|y|) >= 200.

usage: python -I cleanworld.py <scene.json> <arch_model.json> <report.json> <clean_rows.json>
"""
import collections
import json
import math
import struct
import sys

scene, arch_model, out, rows_out = sys.argv[1:5]
inst = json.load(open(scene, encoding="utf-8"))["instances"]
S = [r for r in inst if r["class"] == "S"]
st = [r for r in S if r["strict"]]
clean = [r for r in st if max(abs(r["pos"][0]), abs(r["pos"][1])) >= 200]
bind = {b["archetype_hash"].lower().replace("0x", "") for b in json.load(open(arch_model, encoding="utf-8"))["bindings"]}
names = {r["hash"].lower(): r["archetype"] for r in inst if r.get("archetype")}


def pct(a, q):
    b = sorted(a)
    return b[min(len(b) - 1, int(q * (len(b) - 1)))] if b else 0.0


def f32(h):
    return struct.unpack("<f", struct.pack("<I", int(h, 16)))[0]


def describe(rows):
    xs = [r["pos"][0] for r in rows]
    ys = [r["pos"][1] for r in rows]
    zs = [r["pos"][2] for r in rows]
    rad = [max(abs(a), abs(b)) for a, b in zip(xs, ys)]
    h = collections.Counter(r["hash"].lower() for r in rows)
    d = {"n": len(rows), "resources": len({r["resource"] for r in rows}),
         "x": {"p01": round(pct(xs, .01), 1), "p02": round(pct(xs, .02), 1), "p50": round(pct(xs, .5), 1),
               "p98": round(pct(xs, .98), 1), "p99": round(pct(xs, .99), 1),
               "min": round(min(xs), 1), "max": round(max(xs), 1)},
         "y": {"p01": round(pct(ys, .01), 1), "p02": round(pct(ys, .02), 1), "p50": round(pct(ys, .5), 1),
               "p98": round(pct(ys, .98), 1), "p99": round(pct(ys, .99), 1),
               "min": round(min(ys), 1), "max": round(max(ys), 1)},
         "z": {"p01": round(pct(zs, .01), 1), "p50": round(pct(zs, .5), 1), "p99": round(pct(zs, .99), 1),
               "min": round(min(zs), 1), "max": round(max(zs), 1)},
         "max_abs": {"p50": round(pct(rad, .5), 1), "p90": round(pct(rad, .9), 1),
                     "p98": round(pct(rad, .98), 1), "p99": round(pct(rad, .99), 1),
                     "p999": round(pct(rad, .999), 1), "max": round(max(rad), 1)},
         "beyond_8k": sum(1 for v in rad if v > 8000), "beyond_10k": sum(1 for v in rad if v > 10000),
         "beyond_15k": sum(1 for v in rad if v > 15000), "beyond_20k": sum(1 for v in rad if v > 20000),
         "distinct_2dp": len({(round(r["pos"][0], 2), round(r["pos"][1], 2), round(r["pos"][2], 2)) for r in rows}),
         "distinct_hashes": len(h),
         "float_shaped_distinct": sum(1 for k in h if (lambda f: f == f and ((int(k[2:], 16) & 0x7FFFFF) == 0 or 1e-3 <= abs(f) <= 20000))(f32(k))),
         "named_distinct": sum(1 for k in h if names.get(k)),
         "bound_instances": sum(n for k, n in h.items() if k[2:] in bind),
         "sys": True}
    d["bind_rate"] = round(d["bound_instances"] / d["n"], 6) if d["n"] else 0
    return d


rep = {"s_rows": len(S), "strict_rows": len(st), "clean_world_rows": len(clean),
       "near_origin_strict_rows": len(st) - len(clean),
       "all_s": describe(S), "strict": describe(st), "clean": describe(clean),
       "top20_clean": [{"hash": "0x" + k, "instances": v, "name": names.get(k)}
                       for k, v in collections.Counter(r["hash"].lower() for r in clean).most_common(20)]}
json.dump(rep, open(out, "w", encoding="utf-8"), indent=1)
json.dump({"note": "clean world-space placement: class S, strict yaw/hash test, and >=200 m from the "
                  "origin (origin-adjacent rows are local child tables)",
           "instances": [{k: r[k] for k in ("hash", "pos", "resource", "yaw")} for r in clean]},
          open(rows_out, "w", encoding="utf-8"))
for tag in ("all_s", "strict", "clean"):
    v = rep[tag]
    print(tag, json.dumps({k: v[k] for k in ("n", "resources", "x", "y", "z", "max_abs",
                                             "beyond_10k", "beyond_20k", "distinct_hashes",
                                             "distinct_2dp", "bound_instances", "bind_rate")}, indent=1))
print("top20 clean:", json.dumps(rep["top20_clean"], indent=1))
