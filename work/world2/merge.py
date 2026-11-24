"""Merge wscan2 shards into the full placement dataset + name table + census.

Streaming/bucketed so it works incrementally and does not need the whole set in RAM.
Usage: python -I merge.py <outdir> <scene_json> <names_tsv> <census_json> <bind_report_json>

Buckets are keyed by the low byte of the resource offset; within a bucket exact duplicate rows
(same resource/hash/pos/scale/rot/class) are removed before writing.
"""
import glob
import json
import os
import sys

outdir, scene_json, names_tsv, census_json, bind_json = sys.argv[1:6]
arch_model = sys.argv[6] if len(sys.argv) > 6 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "draw", "out", "arch_model.json")

bucket_dir = os.path.join(outdir, "buckets")
os.makedirs(bucket_dir, exist_ok=True)

shards = sorted(glob.glob(os.path.join(outdir, "inst_*.tsv")))
print(f"shards: {len(shards)}", flush=True)

# ---- pass 1: bucket ----
if not os.path.exists(os.path.join(bucket_dir, ".done")):
    handles = {}
    try:
        for i in range(256):
            handles[i] = open(os.path.join(bucket_dir, f"b{i:02x}.tsv"), "a", encoding="ascii", buffering=1 << 20)
        n = 0
        for sh in shards:
            with open(sh, encoding="ascii", errors="replace") as f:
                for line in f:
                    if not line:
                        continue
                    b = int(line[line.rfind("\t", 0, 12) if False else len(line) - 0:][:0] or 0)
                    res = line.split("\t", 1)[0]
                    handles[int(res[-2:], 16)].write(line)
                    n += 1
                    if n % 5000000 == 0:
                        print(f"  bucketed {n:,}", flush=True)
    finally:
        for h in handles.values():
            h.close()
    open(os.path.join(bucket_dir, ".done"), "w").close()
    print(f"bucketed {n:,} rows", flush=True)

# ---- bind hashes ----
bind_hashes = set()
if os.path.exists(arch_model):
    with open(arch_model, encoding="utf-8") as f:
        doc = json.load(f)
    bind_hashes = {b["archetype_hash"].lower().replace("0x", "") for b in doc["bindings"]}
print(f"bindable archetype hashes: {len(bind_hashes):,}", flush=True)

# ---- pass 2: dedupe, write scene + gather names/census ----
h2n = {}
for line in open(os.path.join(outdir, "decl_*.tsv") if False else glob.glob(os.path.join(outdir, "decl_*.tsv"))[0], encoding="utf-8", errors="replace") if glob.glob(os.path.join(outdir, "decl_*.tsv")) else []:
    pass

for path in glob.glob(os.path.join(outdir, "decl_*.tsv")):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                hv, nm, tag = p[2], p[1], (p[3] if len(p) > 3 else "")
                prev = h2n.get(hv)
                if prev is None or (tag == "#dr" and not prev[1].startswith("#")):
                    h2n[hv] = (nm, tag)

census = {}
total = 0
per_class = {"M": 0, "P": 0, "S": 0}
hash0 = 0
bound = 0
bound_hashes = set()
resources = set()
pos_min = [1e30, 1e30, 1e30]
pos_max = [-1e30, -1e30, -1e30]
dropped = [0, 0]
z_abs_buckets = [0] * 8   # <1,<5,<20,<50,<100,<300,<1000,>=1000

os.makedirs(os.path.dirname(scene_json) or ".", exist_ok=True)
obb_json = scene_json.replace(".json", "_obb.json")
out_obb = open(obb_json, "w", encoding="utf-8")
out_obb.write('{"note":"OBB/collision records from big 0DRP blocks: vec4 posA, vec4 posB, 3x vec4 matrix; the record carries no archetype hash","instances":[')
obb_first = True
with open(scene_json, "w", encoding="utf-8") as out:
    out.write('{"note":"every entity instance found by the full 440,753-candidate levels.rpf scan; '
              'class M = pointer+joaat-verified archetype name, P = unnamed repeated-hash array '
              '(exterior/index class), S = 0DRP street position stream","instances":[')
    first = True
    for bi in range(256):
        bp = os.path.join(bucket_dir, f"b{bi:02x}.tsv")
        if not os.path.exists(bp):
            continue
        seen = set()
        with open(bp, encoding="ascii", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line in seen:
                    continue
                seen.add(line)
                p = line.split("\t")
                if len(p) < 13:
                    continue
                res, hv, x, y, z, sx, sy, sz, qx, qy, qz, qw, cls = p[:13]
                name = p[13] if len(p) > 13 else ""
                hv = hv.lower()
                if hv == "00000000":
                    hash0 += 1
                if name:
                    h2n.setdefault(hv, (name, ""))
                nm = h2n.get(hv, (None, ""))[0]
                if cls == "S" and abs(float(z)) < 1e-6:
                    dropped[1] += 1
                    continue
                if cls == "S" and (0x3C000000 <= int(hv, 16) < 0x43000000 or 0xBB000000 < int(hv, 16) < 0xC3000000):
                    dropped[0] += 1
                    continue
                if cls == "P":
                    if not obb_first:
                        out_obb.write(",")
                    obb_first = False
                    out_obb.write('{"hash":"0x' + hv + '","pos":[' + x + "," + y + "," + z + '],"resource":"0x' + res + '","class":"P"}')
                    per_class["P"] = per_class.get("P", 0) + 1
                    resources.add(res)
                    continue
                if not first:
                    out.write(",")
                first = False
                out.write('{"archetype":')
                out.write(json.dumps(nm) if nm else "null")
                out.write(',"hash":"0x')
                out.write(hv)
                out.write('","pos":[')
                out.write(x); out.write(","); out.write(y); out.write(","); out.write(z)
                out.write('],"rot":[')
                out.write(qx); out.write(","); out.write(qy); out.write(","); out.write(qz); out.write(","); out.write(qw)
                out.write('],"scale":[')
                out.write(sx); out.write(","); out.write(sy); out.write(","); out.write(sz)
                out.write('],"resource":"0x')
                out.write(res)
                out.write('","class":"')
                out.write(cls)
                out.write('"}')
                total += 1
                per_class[cls] = per_class.get(cls, 0) + 1
                resources.add(res)
                if hv in bind_hashes:
                    bound += 1
                    bound_hashes.add(hv)
                census[hv] = census.get(hv, 0) + 1
                fx, fy, fz = float(x), float(y), float(z)
                pos_min = [min(pos_min[0], fx), min(pos_min[1], fy), min(pos_min[2], fz)]
                pos_max = [max(pos_max[0], fx), max(pos_max[1], fy), max(pos_max[2], fz)]
                az = abs(fz)
                idx = 0 if az < 1 else 1 if az < 5 else 2 if az < 20 else 3 if az < 50 else 4 if az < 100 else 5 if az < 300 else 6 if az < 1000 else 7
                z_abs_buckets[idx] += 1
                if total % 10000000 == 0:
                    print(f"  merged {total:,}", flush=True)
    out.write("]}")
out_obb.write("]}")

out_obb.close()
with open(names_tsv, "w", encoding="utf-8") as f:
    f.write("hash\tname\ttag\n")
    for hv, (nm, tag) in sorted(h2n.items()):
        f.write(f"0x{hv}\t{nm}\t{tag}\n")

top = sorted(census.items(), key=lambda kv: -kv[1])[:200]
with open(census_json, "w", encoding="utf-8") as f:
    json.dump([{"hash": "0x" + h, "name": h2n.get(h, (None, ""))[0], "instances": c} for h, c in top], f, indent=1)

report = {
    "instances": total, "zero_z_s_dropped": dropped[1], "floatish_s_dropped": dropped[0], "resources": len(resources), "hash_zero": hash0,
    "per_class": per_class, "distinct_hashes": len(census),
    "named_distinct_hashes": sum(1 for h in census if h in h2n),
    "bound_instances": bound, "bound_distinct_hashes": len(bound_hashes),
    "bound_rate": bound / total if total else 0,
    "pos_min": pos_min, "pos_max": pos_max,
    "z_abs_hist": {"lt1": z_abs_buckets[0], "lt5": z_abs_buckets[1], "lt20": z_abs_buckets[2],
                   "lt50": z_abs_buckets[3], "lt100": z_abs_buckets[4], "lt300": z_abs_buckets[5],
                   "lt1000": z_abs_buckets[6], "ge1000": z_abs_buckets[7]},
    "names_total": len(h2n),
}
json.dump(report, open(bind_json, "w", encoding="utf-8"), indent=1)
print(json.dumps(report, indent=1))
