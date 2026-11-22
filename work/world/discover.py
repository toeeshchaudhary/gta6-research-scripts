"""Brute-force record-layout discovery on one resource blob.

For every (stride, arrayStart, posField, hashField) find the longest run of records with a
plausible float3 position and a plausible joaat hash, and report the best few layouts with
sample positions and resolved names.

usage: python -I discover.py <archive> <offsetHex> <names.tsv>
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


arch, off, namefile = sys.argv[1], int(sys.argv[2], 16), sys.argv[3]

h2n = {}
for line in open(namefile, encoding="utf-8", errors="replace"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 2:
        continue
    n = p[1]
    for cand in (n, n.split(".")[0], n.replace(".#ft", "")):
        if cand:
            h2n.setdefault(joaat(cand), cand)

with open(arch, "rb", buffering=0) as f:
    f.seek(off)
    mem = zlib.decompressobj().decompress(f.read(4 << 20))
print(f"blob 0x{off:X} {len(mem):,} bytes")

LIM = len(mem) - 16
results = []


def plausible(v):
    return v == v and abs(v) < 20000 and (v == 0 or abs(v) > 1e-25)


for stride in range(16, 260, 4):
    for start in range(0, min(stride, 64), 4):
        words = stride // 4
        for pf in range(words - 3):
            for hf in range(words):
                if pf <= hf <= pf + 2:
                    continue
                n = 0
                minx = miny = 1e30
                maxx = maxy = -1e30
                good = 0
                while True:
                    o = start + n * stride
                    if o + stride > LIM:
                        break
                    x, y, z = struct.unpack_from("<3f", mem, o + pf * 4)
                    if not (plausible(x) and plausible(y) and plausible(z)):
                        break
                    if x == 0 and y == 0 and z == 0:
                        break
                    hv = struct.unpack_from("<I", mem, o + hf * 4)[0]
                    if hv < 0x10000:
                        break
                    if hv in h2n:
                        good += 1
                    n += 1
                    minx = min(minx, x); maxx = max(maxx, x)
                    miny = min(miny, y); maxy = max(maxy, y)
                if n < 20:
                    continue
                span = max(maxx - minx, maxy - miny)
                if span < 0.5:
                    continue
                results.append((good, n, span, stride, start, pf * 4, hf * 4, minx, maxx, miny, maxy))

results.sort(key=lambda r: (-r[0], -r[1]))
print(f"layouts found: {len(results)}")
seen = set()
for good, n, span, stride, start, po, ho, x0, x1, y0, y1 in results[:400]:
    if (stride, po, ho) in seen:
        continue
    seen.add((stride, po, ho))
    print(f"  stride={stride:3} start={start:2} pos+{po:3} hash+{ho:3} n={n:5} resolved={good:5} "
          f"span={span:9.1f} x[{x0:9.1f},{x1:9.1f}] y[{y0:9.1f},{y1:9.1f}]")
    if len(seen) >= 6:
        break

if not results:
    sys.exit(0)

good, n, span, stride, start, po, ho, *_ = results[0]
print(f"\n=== decode stride={stride} start={start} pos+{po} hash+{ho} ===")
for r in range(min(n, 12)):
    o = start + r * stride
    x, y, z = struct.unpack_from("<3f", mem, o + po)
    hv = struct.unpack_from("<I", mem, o + ho)[0]
    print(f"  rec{r:3}@{o:06X} ({x:9.3f},{y:9.3f},{z:8.3f})  0x{hv:08X} {h2n.get(hv, '?')}")
