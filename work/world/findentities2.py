"""Entity-array finder v2.

Position is taken to be at the record start (verified for GTA VI's 80-byte entity record).
A real world-placement array must span a 2-D area (not a 1-D path) and stay nearly planar
in height. For each candidate layout we also report how many archetype hashes resolve.

usage: python -I findentities2.py <archive> <candidates.txt> <names.tsv> [maxBlobs] [minSpan]
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
minspan = float(sys.argv[5]) if len(sys.argv) > 5 else 150.0

h2n = {}
for line in open(namefile, encoding="utf-8", errors="replace"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 2:
        continue
    n = p[1]
    for cand in (n, n.split(".")[0], n.replace(".#ft", "")):
        if cand:
            h2n.setdefault(joaat(cand), cand)
print(f"name hashes {len(h2n):,}", flush=True)


def plausible(v):
    return v == v and abs(v) < 20000 and (v == 0 or abs(v) > 1e-25)


scanned = hits = 0
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
        for stride in range(64, 140, 4):
            for start in range(0, stride, 4):
                n = 0
                x0 = y0 = z0 = 1e30
                x1 = y1 = z1 = -1e30
                while True:
                    o = start + n * stride
                    if o + stride > len(mem) - 8:
                        break
                    x, y, z = struct.unpack_from("<3f", mem, o)
                    if not (plausible(x) and plausible(y) and plausible(z)):
                        break
                    if x == 0 and y == 0 and z == 0:
                        break
                    n += 1
                    x0 = min(x0, x); x1 = max(x1, x)
                    y0 = min(y0, y); y1 = max(y1, y)
                    z0 = min(z0, z); z1 = max(z1, z)
                if n < 32:
                    continue
                sx, sy, sz = x1 - x0, y1 - y0, z1 - z0
                if sx < minspan or sy < minspan or sz > 400:
                    continue
                if best is None or n > best[0]:
                    best = (n, stride, start, sx, sy, sz, x0, x1, y0, y1, z0, z1)
        if best is None:
            continue
        n, stride, start, sx, sy, sz, x0, x1, y0, y1, z0, z1 = best
        # hash column: best resolution count over all field offsets
        bh = bhits = 0
        bho = -1
        for ho in range(4, stride - 4, 4):
            c = 0
            for r in range(n):
                if struct.unpack_from("<I", mem, start + r * stride + ho)[0] in h2n:
                    c += 1
            if c > bhits:
                bhits, bho = c, ho
        hits += 1
        print(f"0x{off:X} len={len(mem):,} stride={stride} start={start} n={n} "
              f"x[{x0:.0f},{x1:.0f}]({sx:.0f}) y[{y0:.0f},{y1:.0f}]({sy:.0f}) z[{z0:.1f},{z1:.1f}] "
              f"hash+{bho} resolved={bhits}", flush=True)
        for r in range(min(3, n)):
            o = start + r * stride
            x, y, z = struct.unpack_from("<3f", mem, o)
            nm = h2n.get(struct.unpack_from("<I", mem, o + bho)[0], "?") if bho >= 0 else "?"
            print(f"     ({x:10.2f},{y:10.2f},{z:8.2f})  {nm}", flush=True)
print(f"findentities2: {hits} planar 2-D arrays in {scanned} blobs")
