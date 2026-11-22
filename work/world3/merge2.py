"""Merge patched-scan shards: scene with yaw+strict, names, census, bind, extent, float shares.

Columns of the shards: res  hash  x  y  z  scale3  quat4  class  name  yaw  strict

usage: python -I merge2.py <outdir> <scene_json> <names_tsv> <census_json> <report_json> <arch_model>
"""
import glob
import json
import os
import struct
import sys
import zlib

outdir, scene_json, names_tsv, census_json, report_json, arch_model = sys.argv[1:7]
os.makedirs(os.path.dirname(scene_json) or ".", exist_ok=True)

shards = sorted(glob.glob(os.path.join(outdir, "inst_*.tsv")))
print(f"shards {len(shards)}", flush=True)

bind = {b["archetype_hash"].lower().replace("0x", "") for b in json.load(open(arch_model, encoding="utf-8"))["bindings"]}
h2n = {}
for path in glob.glob(os.path.join(outdir, "decl_*.tsv")):
    for line in open(path, encoding="utf-8", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3:
            h2n.setdefault(p[2].lower(), p[1])
print(f"declared names {len(h2n):,} bindable {len(bind):,}", flush=True)


def cff(v):
    f = struct.unpack("<f", struct.pack("<I", v))[0]
    return f == f and 0.01 <= abs(f) <= 20000.0


seen_lines = set()
tot = {"M": 0, "P": 0, "S": 0}
strict = {"M": 0, "P": 0, "S": 0}
unstrict = {"M": 0, "P": 0, "S": 0}
census = {"S": {}, "M": {}, "P": {}}
census_strict = {"S": {}}
binds = {"S": 0, "M": 0, "M_all": 0}
bind_hashes = {"S": set()}
resources = set()
zero_rows = 0
pos = {"S": [], "M": [], "P": [], "S_strict": []}
zb = [0] * 8

obb_path = scene_json.replace(".json", "_obb.json")
out_obb = open(obb_path, "w", encoding="utf-8")
out_obb.write('{"note":"OBB/collision family records (vec4 posA/posB/3x mat), no archetype hash; strict is the same test applied to the id slot and is NOT meaningful here","instances":[')
obb_first = True

with open(scene_json, "w", encoding="utf-8") as out:
    out.write('{"note":"complete-data levels.rpf scan: every one of the 508,767 candidates on the '
              'final 76,155,065,056-byte file. class M = joaat-verified local interior/MLO child, '
              'P = unnamed repeated-hash array, S = world-space 0DRP placement. yaw = float at +0x0C; '
              'strict = 1 when the record passes the yaw-range (|yaw|<=3.19) and non-float-hash test, '
              'i.e. is a genuine placement record","instances":[')
    first = True
    n = 0
    for sh in shards:
        for line in open(sh, encoding="ascii", errors="replace"):
            line = line.rstrip("\n")
            if not line:
                continue
            k = zlib.crc32(line.encode("ascii", "replace"))
            if k in seen_lines:
                continue
            seen_lines.add(k)
            p = line.split("\t")
            if len(p) < 15:
                continue
            res, hv, x, y, z, sx, sy, sz, qx, qy, qz, qw, cls, name, yaw, sflag = p[:16]
            hv = hv.lower()
            if hv == "00000000":
                zero_rows += 1
            if name:
                h2n.setdefault(hv, name)
            nm = h2n.get(hv)
            st = sflag == "1"
            if cls == "S":
                if abs(float(z)) < 1e-6:
                    continue
                if 0x3C000000 <= int(hv, 16) < 0x43000000 or 0xBB000000 < int(hv, 16) < 0xC3000000:
                    continue
            tot[cls] += 1
            (strict if st else unstrict)[cls] += 1
            resources.add(res)
            census[cls][hv] = census[cls].get(hv, 0) + 1
            if cls == "S":
                if st:
                    census_strict["S"][hv] = census_strict["S"].get(hv, 0) + 1
                    if hv in bind:
                        binds["S"] += 1
                        bind_hashes["S"].add(hv)
                pos["S"].append((float(x), float(y), float(z)))
                if st:
                    pos["S_strict"].append((float(x), float(y), float(z)))
                az = abs(float(z))
                zb[0 if az < 1 else 1 if az < 5 else 2 if az < 20 else 3 if az < 50 else 4 if az < 100 else 5 if az < 300 else 6 if az < 1000 else 7] += 1
            elif cls == "M":
                pos["M"].append((float(x), float(y), float(z)))
                if hv in bind:
                    binds["M_all"] += 1
                    if st:
                        binds["M"] += 1
            if cls == "P":
                if not obb_first:
                    out_obb.write(",")
                obb_first = False
                out_obb.write('{"hash":"0x%s","pos":[%s,%s,%s],"resource":"0x%s","class":"P","strict":%s}'
                              % (hv, x, y, z, res, "true" if st else "false"))
                continue
            if not first:
                out.write(",")
            first = False
            out.write('{"archetype":%s,"hash":"0x%s","pos":[%s,%s,%s],"rot":[%s,%s,%s,%s],"scale":[%s,%s,%s],'
                      '"resource":"0x%s","class":"%s","yaw":%s,"strict":%s}'
                      % (json.dumps(nm) if nm else "null", hv, x, y, z, qx, qy, qz, qw, sx, sy, sz,
                         res, cls, yaw, "true" if st else "false"))
            n += 1
            if n % 500000 == 0:
                print(f"  merged {n:,}", flush=True)
    out.write("]}")
out_obb.write("]}")
out_obb.close()


def pct(a, q):
    b = sorted(a)
    return b[min(len(b) - 1, int(q * (len(b) - 1)))] if b else 0.0


rep = {"rows": n, "resources": len(resources), "hash_zero_rows": zero_rows,
       "per_class": tot, "strict": strict, "unstrict": unstrict,
       "strict_frac": {k: round(strict[k] / tot[k], 4) if tot[k] else 0 for k in tot},
       "distinct_hashes": {k: len(v) for k, v in census.items()},
       "distinct_hashes_strict_s": len(census_strict["S"]),
       "named_distinct": {k: sum(1 for h in v if h in h2n) for k, v in census.items()},
       "coord_float_distinct": {k: sum(1 for h in v if cff(int(h, 16))) for k, v in census.items()},
       "coord_float_distinct_frac": {k: round(sum(1 for h in v if cff(int(h, 16))) / len(v), 4) if v else 0 for k, v in census.items()},
       "bind_instances": binds, "bind_rate_s": round(binds["S"] / tot["S"], 6) if tot["S"] else 0,
       "bind_rate_total": round((binds["S"] + binds["M"]) / n, 6) if n else 0,
       "bind_distinct_hashes_s": len(bind_hashes["S"]),
       "z_abs_hist": {"lt1": zb[0], "lt5": zb[1], "lt20": zb[2], "lt50": zb[3], "lt100": zb[4],
                      "lt300": zb[5], "lt1000": zb[6], "ge1000": zb[7]},
       "top20_s_strict": [{"hash": "0x" + h, "instances": c, "name": h2n.get(h)} for h, c in sorted(census_strict["S"].items(), key=lambda kv: -kv[1])[:20]],
       "top20_s_all": [{"hash": "0x" + h, "instances": c, "name": h2n.get(h)} for h, c in sorted(census["S"].items(), key=lambda kv: -kv[1])[:20]],
       }
for cls in ("S", "S_strict", "M"):
    xs = [p[0] for p in pos[cls]]
    ys = [p[1] for p in pos[cls]]
    zs = [p[2] for p in pos[cls]]
    rep["extent_" + cls] = {"n": len(xs),
                            "x_min": round(min(xs), 1) if xs else 0, "x_max": round(max(xs), 1) if xs else 0,
                            "y_min": round(min(ys), 1) if ys else 0, "y_max": round(max(ys), 1) if ys else 0,
                            "x_p02": round(pct(xs, .02), 1), "x_p50": round(pct(xs, .5), 1), "x_p98": round(pct(xs, .98), 1),
                            "y_p02": round(pct(ys, .02), 1), "y_p50": round(pct(ys, .5), 1), "y_p98": round(pct(ys, .98), 1),
                            "p99_max_abs": round(pct([max(abs(a), abs(b)) for a, b in zip(xs, ys)], .99), 1) if xs else 0,
                            "distinct_2dp": len({(round(a, 2), round(b, 2), round(c, 2)) for a, b, c in zip(xs, ys, zs)})}
json.dump(rep, open(report_json, "w", encoding="utf-8"), indent=1)
with open(names_tsv, "w", encoding="utf-8") as f:
    f.write("hash\tname\n")
    for hv, nm in sorted(h2n.items()):
        f.write(f"0x{hv}\t{nm}\n")
json.dump([{"hash": "0x" + h, "instances": c, "name": h2n.get(h)} for h, c in sorted(census_strict["S"].items(), key=lambda kv: -kv[1])[:200]],
          open(census_json, "w", encoding="utf-8"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if not k.startswith("top20")}, indent=1))
