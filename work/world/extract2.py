"""Extract entity instances from hits20k.tsv (fast C# detector output).

Record template verified against bytes (see WORLD.md):
  position float3 @ +posOff, archetype joaat hash @ +hashOff (relative to record start).
When posOff == 0 the verified GTA VI 80-byte record applies, so scale (+0x10) and the
rotation quaternion (+0x40) are read too.

usage: python -I extract2.py <archive> <hits.tsv> <names.tsv> <out.json>
"""
import json
import struct
import sys
import zlib


def joaat(s):
    h = 0
    for c in s.lower().encode("latin-1", "replace"):
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF


arch, hitsFile, nameFile, outFile = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

h2n = {}
for line in open(nameFile, encoding="utf-8", errors="replace"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 2:
        continue
    n = p[1]
    for cand in (n, n.split(".")[0], n.replace(".#ft", "")):
        if cand:
            h2n.setdefault(joaat(cand), cand)

rows = []
for line in open(hitsFile, encoding="utf-8", errors="replace"):
    p = line.split()
    if len(p) < 5:
        continue
    rows.append((int(p[0], 16), int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5])))
print(f"resources: {len(rows)}")

instances = []
res_count = 0
resources = []
with open(arch, "rb", buffering=0) as fh:
    for off, stride, start, n, posOff, hashOff in rows:
        fh.seek(off)
        try:
            mem = zlib.decompressobj().decompress(fh.read(1 << 21))
        except Exception:
            continue
        kept = 0
        named = 0
        for r in range(n):
            o = start + r * stride
            if o + stride > len(mem):
                break
            try:
                x, y, z = struct.unpack_from("<3f", mem, o + posOff)
            except Exception:
                break
            if not all(v == v and abs(v) < 30000 for v in (x, y, z)):
                continue
            hv = struct.unpack_from("<I", mem, o + hashOff)[0]
            name = h2n.get(hv)
            if name:
                named += 1
                res_count += 1
            scale = [1.0, 1.0, 1.0]
            rot = [0.0, 0.0, 0.0, 1.0]
            if posOff == 0 and stride >= 80:
                sx, sy, sz = struct.unpack_from("<3f", mem, o + 0x10)
                if all(0.01 < v < 100 for v in (sx, sy, sz)):
                    scale = [round(sx, 4), round(sy, 4), round(sz, 4)]
                qx, qy, qz, qw = struct.unpack_from("<4f", mem, o + 0x40)
                if all(abs(v) <= 1.5 for v in (qx, qy, qz, qw)):
                    nq = (qx * qx + qy * qy + qz * qz + qw * qw) ** 0.5
                    if 0.9 < nq < 1.1:
                        rot = [round(qx, 5), round(qy, 5), round(qz, 5), round(qw, 5)]
            instances.append({
                "archetype": name,
                "hash": f"0x{hv:08X}",
                "pos": [round(x, 3), round(y, 3), round(z, 3)],
                "rot": rot,
                "scale": scale,
                "resource": f"0x{off:X}",
            })
            kept += 1
        if kept:
            resources.append({"resource": f"0x{off:X}", "instances": kept, "named": named,
                              "stride": stride, "posField": posOff})

doc = {
    "source": arch,
    "generated_by": "work/world/extract2.py",
    "format": "GTA VI RPF9 resource system blobs -> fixed-stride entity instance records",
    "verified_record": {
        "size": 80,
        "position": "float3 @ +0x00  (x, y, z)",
        "archetype": "uint32 joaat @ +0x0C",
        "scale": "float3 @ +0x10",
        "rotation": "float4 quaternion @ +0x40",
    },
    "counts": {
        "instances": len(instances),
        "with_name": sum(1 for i in instances if i["archetype"]),
        "distinct_archetypes": len({i["archetype"] for i in instances if i["archetype"]}),
        "resources": len(resources),
    },
    "resources": resources,
    "instances": instances,
}
json.dump(doc, open(outFile, "w", encoding="utf-8"), indent=1)
c = doc["counts"]
print(f"{c['instances']} instances, {c['with_name']} named, "
      f"{c['distinct_archetypes']} distinct archetypes, {c['resources']} resources")

