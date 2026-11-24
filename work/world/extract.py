"""Extract entity instances from the named entity-array hits found by findentities3.py.

Emits JSON: {source_archive, note, instances:[{archetype, hash, pos:[x,y,z], rot:[x,y,z,w],
scale:[x,y,z], resource, record}], stats:{...}}

usage: python -I extract.py <archive> <hits.txt> <names.tsv> <out.json> [maxPerBlob]
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
maxPer = int(sys.argv[5]) if len(sys.argv) > 5 else 100000

h2n = {}
for line in open(nameFile, encoding="utf-8", errors="replace"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 2:
        continue
    n = p[1]
    for cand in (n, n.split(".")[0], n.replace(".#ft", "")):
        if cand:
            h2n.setdefault(joaat(cand), cand)

hits = []
raw = open(hitsFile, "rb").read()
if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
    text = raw.decode("utf-16", errors="replace")
else:
    text = raw.decode("utf-8", errors="replace")
for line in text.splitlines():
    if not line.startswith("0x"):
        continue
    f = {}
    for tok in line.split():
        if tok.startswith("0x") and "=" not in tok:
            f["off"] = int(tok, 16)
        elif "=" in tok:
            k, v = tok.split("=", 1)
            f[k] = v
    hits.append(f)
print(f"hits: {len(hits)}")

instances = []
resolved = 0
per_resource = []
with open(arch, "rb", buffering=0) as fh:
    for h in hits:
        off = h["off"]
        stride = int(h["stride"])
        start = int(h["start"])
        ho = int(h["hash"][1:])
        n = int(h["n"])
        fh.seek(off)
        try:
            mem = zlib.decompressobj().decompress(fh.read(1 << 21))
        except Exception:
            continue
        kept = 0
        for r in range(min(n, maxPer)):
            o = start + r * stride
            if o + 4 > len(mem):
                break
            x, y, z = struct.unpack_from("<3f", mem, o)
            if not all(v == v and abs(v) < 20000 for v in (x, y, z)):
                continue
            hv = struct.unpack_from("<I", mem, o + ho)[0]
            name = h2n.get(hv)
            if name:
                resolved += 1
            scale = [1.0, 1.0, 1.0]
            rot = [0.0, 0.0, 0.0, 1.0]
            if stride >= 80:
                try:
                    sx, sy, sz = struct.unpack_from("<3f", mem, o + 0x10)
                    if all(0.01 < v < 100 for v in (sx, sy, sz)):
                        scale = [sx, sy, sz]
                    qx, qy, qz, qw = struct.unpack_from("<4f", mem, o + 0x40)
                    if all(abs(v) <= 1.5 for v in (qx, qy, qz, qw)):
                        nq = (qx * qx + qy * qy + qz * qz + qw * qw) ** 0.5
                        if 0.9 < nq < 1.1:
                            rot = [qx, qy, qz, qw]
                except Exception:
                    pass
            instances.append({
                "archetype": name,
                "hash": f"0x{hv:08X}",
                "pos": [round(x, 4), round(y, 4), round(z, 4)],
                "rot": [round(v, 5) for v in rot],
                "scale": [round(v, 4) for v in scale],
                "resource": f"0x{off:X}",
                "record": r,
            })
            kept += 1
        per_resource.append((f"0x{off:X}", kept))

doc = {
    "source_archive": arch,
    "format": "GTA VI RPF9 resource system blobs -> 80-byte entity instance records",
    "verified_fields": {
        "position": "+0x00 float3 (x, y, z)",
        "archetype_hash": "+0x0C uint32 joaat",
        "scale": "+0x10 float3",
        "rotation": "+0x40 float4 quaternion",
    },
    "counts": {
        "instances": len(instances),
        "with_name": sum(1 for i in instances if i["archetype"]),
        "distinct_archetypes": len({i["archetype"] for i in instances if i["archetype"]}),
        "resources": len(per_resource),
    },
    "instances": instances,
}
with open(outFile, "w", encoding="utf-8") as w:
    json.dump(doc, w, indent=1)
print(f"wrote {outFile}: {len(instances)} instances, {doc['counts']['with_name']} named, "
      f"{doc['counts']['distinct_archetypes']} distinct archetypes, {len(per_resource)} resources")
