"""Find real entity-instance arrays: fixed-stride records with a float3 position AND an
archetype hash that resolves to a known model/prop name.

usage: python -I findentities.py <archive> <candidates.txt> <names.tsv> [maxBlobs]
"""
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


arch, candfile, namefile = sys.argv[1], sys.argv[2], sys.argv[3]
maxblobs = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9

h2n = {}
for line in open(namefile, encoding="utf-8", errors="replace"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 2:
        continue
    n = p[1]
    for cand in (n, n.split(".")[0], n.replace(".#ft", "")):
        if cand:
            h2n.setdefault(joaat(cand), cand)

tracker_path = arch + ".pos"
with open(tracker_path, "rb") as t:
    tracker = t.read()
print(f"name hashes {len(h2n):,}  (file-mtime tracker {len(tracker)} bytes)")

STRIDES = [80, 84, 88, 92, 96, 100, 104, 108, 112, 120, 128, 136, 144, 152, 160]


def plausible(v):
    return v == v and abs(v) < 20000 and (v == 0 or abs(v) > 1e-25)


hits = 0
scanned = 0
with open(arch, "rb", buffering=0) as f:
    for line in open(candfile):
        line = line.strip()
        if not line:
            continue
        if scanned >= maxblobs:
            break
        off = int(line, 16)
        f.seek(off)
        try:
            mem = zlib.decompressobj().decompress(f.read(1 << 20))
        except Exception:
            continue
        scanned += 1
        best = None
        for stride in STRIDES:
            for start in range(0, min(stride, 32), 4):
                for ho in range(4, stride - 4, 4):
                    n = 0
                    res = 0
                    minx = miny = minz = 1e30
                    maxx = maxy = maxz = -1e30
                    while True:
                        o = start + n * stride
                        if o + stride > len(mem) - 8:
                            break
                        x, y, z = struct.unpack_from("<3f", mem, o)
                        if not (plausible(x) and plausible(y) and plausible(z)):
                            break
                        if x == 0 and y == 0 and z == 0:
                            break
                        if struct.unpack_from("<I", mem, o + ho)[0] in h2n:
                            res += 1
                        n += 1
                        minx = min(minx, x); maxx = max(maxx, x)
                        miny = min(miny, y); maxy = max(maxy, y)
                        minz = min(minz, z); maxz = max(maxz, z)
                    if n < 16 or res < 8:
                        continue
                    if best is None or res > best[0]:
                        best = (res, n, stride, start, ho, minx, maxx, miny, maxy, minz, maxz)
        if best is None:
            continue
        res, n, stride, start, ho, x0, x1, y0, y1, z0, z1 = best
        hits += 1
        print(f"0x{off:X} len={len(mem):,} stride={stride} start={start} hash+{ho} n={n} resolved={res} "
              f"x[{x0:.1f},{x1:.1f}] y[{y0:.1f},{y1:.1f}] z[{z0:.1f},{z1:.1f}]")
        for r in range(min(3, n)):
            o = start + r * stride
            x, y, z = struct.unpack_from("<3f", mem, o)
            hv = struct.unpack_from("<I", mem, o + ho)[0]
            print(f"     ({x:10.2f},{y:10.2f},{z:8.2f})  {h2n.get(hv, '?')}")
print(f"findentities: {hits} entity arrays in {scanned} blobs")
