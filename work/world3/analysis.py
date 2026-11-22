"""Clean-subset analysis: resource-level purity, extent verdict, census, bind.

Records differ in quality by *resource*: a placement resource has yaw in +-pi for (almost) every row,
while a float/geometry family has arbitrary floats in the yaw slot. So we classify resources by the
fraction of their rows that pass the per-record test and take the extent of the pure ones.

usage: python -I analysis.py <scene.json> <arch_model.json> <report.json>
"""
import collections
import json
import struct
import sys

scene, arch_model, out = sys.argv[1:4]
inst = json.load(open(scene, encoding="utf-8"))["instances"]
S = [r for r in inst if r["class"] == "S"]
print(f"S rows {len(S):,}")

per = collections.defaultdict(lambda: [0, 0])   # res -> [rows, strict rows]
for r in S:
    p = per[r["resource"]]
    p[0] += 1
    p[1] += 1 if r["strict"] else 0

pure = {k for k, v in per.items() if v[1] / v[0] >= 0.90 and v[0] >= 8}
mixed = {k for k, v in per.items() if v[1] / v[0] < 0.90 and k not in pure}
print(f"pure resources {len(pure)} mixed {len(mixed)}")

P = [r for r in S if r["resource"] in pure]
X = [r for r in S if r["resource"] not in pure]


def pct(a, q):
    b = sorted(a)
    return b[min(len(b) - 1, int(q * (len(b) - 1)))] if b else 0.0


def describe(rows, tag):
    xs = [r["pos"][0] for r in rows]
    ys = [r["pos"][1] for r in rows]
    zs = [r["pos"][2] for r in rows]
    rad = [max(abs(a), abs(b)) for a, b in zip(xs, ys)]
    d = {"n": len(rows), "resources": len({r["resource"] for r in rows})}
    d["x"] = {"min": round(min(xs), 1), "p02": round(pct(xs, .02), 1), "p50": round(pct(xs, .5), 1),
              "p98": round(pct(xs, .98), 1), "max": round(max(xs), 1)}
    d["y"] = {"min": round(min(ys), 1), "p02": round(pct(ys, .02), 1), "p50": round(pct(ys, .5), 1),
              "p98": round(pct(ys, .98), 1), "max": round(max(ys), 1)}
    d["z"] = {"min": round(min(zs), 1), "p01": round(pct(zs, .01), 1), "p50": round(pct(zs, .5), 1),
              "p99": round(pct(zs, .99), 1), "max": round(max(zs), 1)}
    d["max_abs"] = {"p50": round(pct(rad, .5), 1), "p95": round(pct(rad, .95), 1),
                    "p99": round(pct(rad, .99), 1), "p999": round(pct(rad, .999), 1), "max": round(max(rad), 1)}
    d["beyond_10k"] = sum(1 for v in rad if v > 10000)
    d["beyond_20k"] = sum(1 for v in rad if v > 20000)
    d["distinct_2dp"] = len({(round(r["pos"][0], 2), round(r["pos"][1], 2), round(r["pos"][2], 2)) for r in rows})
    h = collections.Counter(r["hash"].lower() for r in rows)
    d["distinct_hashes"] = len(h)
    d["top10"] = [{"hash": "0x" + k, "instances": v} for k, v in h.most_common(10)]
    print(tag, json.dumps({k: v for k, v in d.items() if k != "top10"}))
    return d


rep = {"s_rows": len(S), "pure_resources": len(pure), "mixed_resources": len(mixed),
       "pure": describe(P, "PURE "), "mixed": describe(X, "MIXED")}

bind = {b["archetype_hash"].lower().replace("0x", "") for b in json.load(open(arch_model, encoding="utf-8"))["bindings"]}
rep["bind"] = {
    "all_s": {"instances": len(S), "bound": sum(1 for r in S if r["hash"][2:].lower() in bind)},
    "pure": {"instances": len(P), "bound": sum(1 for r in P if r["hash"][2:].lower() in bind)},
    "mixed": {"instances": len(X), "bound": sum(1 for r in X if r["hash"][2:].lower() in bind)},
}
for k, v in rep["bind"].items():
    v["rate"] = round(v["bound"] / v["instances"], 6) if v["instances"] else 0

# street-hash sanity check
for hh in ("0x2f7e64d1", "0xfd378044", "0xd3e22d9a"):
    rep.setdefault("street_hashes", {})[hh] = sum(1 for r in S if r["hash"].lower() == hh)

json.dump(rep, open(out, "w", encoding="utf-8"), indent=1)
print(json.dumps(rep["bind"], indent=1))
print("street", rep["street_hashes"])
