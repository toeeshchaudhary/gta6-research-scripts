"""findentities3: longest-run entity-array finder.

For every stride and every phase, walk the whole blob and keep the longest run of records
whose first 12 bytes are a plausible float3 position. Then count how many archetype hashes
(hash field at some offset) resolve to a known name. Reports runs with real names.

usage: python -I findentities3.py <archive> <candidates.txt> <names.tsv> [maxBlobs] [minResolved]
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
minres = int(sys.argv[5]) if len(sys.argv) > 5 else 8

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

STRIDES = [64, 68, 72, 76, 80, 84, 88, 92, 96, 100, 104, 108, 112, 120, 128, 136, 144, 152, 160]


def ok(v):
    return v == v and abs(v) < 20000 and (v == 0 or abs(v) > 1e-25)


scanned = hits = 0
out = open(candfile + ".fe3.txt", "w", encoding="utf-8")
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
            mem = zlib.decompressobj().decompress(f.read(1 << 21))
        except Exception:
            continue
        scanned += 1
        limit = len(mem) - 96
        best = None
        for stride in STRIDES:
            for phase in range(0, min(stride, 160), 4):
                run = 0
                runstart = 0
                o = phase
                while o < limit:
                    x, y, z = struct.unpack_from("<3f", mem, o)
                    if ok(x) and ok(y) and ok(z) and not (x == 0 and y == 0 and z == 0):
                        if run == 0:
                            runstart = o
                        run += 1
                        if best is None or run > best[0]:
                            best = (run, stride, phase, runstart)
                    else:
                        run = 0
                    o += stride
        if best is None or best[0] < 16:
            continue
        run, stride, phase, runstart = best
        # which field resolves as an archetype hash column?
        bho, bres = -1, 0
        for ho in range(4, stride - 4, 4):
            c = 0
            for r in range(run):
                if struct.unpack_from("<I", mem, runstart + r * stride + ho)[0] in h2n:
                    c += 1
            if c > bres:
                bres, bho = c, ho
        if bres < minres:
            continue
        hits += 1
        xs = [struct.unpack_from("<3f", mem, runstart + r * stride) for r in range(run)]
        x0, x1 = min(p[0] for p in xs), max(p[0] for p in xs)
        y0, y1 = min(p[1] for p in xs), max(p[1] for p in xs)
        z0, z1 = min(p[2] for p in xs), max(p[2] for p in xs)
        lineout = (f"0x{off:X} len={len(mem):,} stride={stride} start={runstart} hash+{bho} n={run} "
                   f"resolved={bres} x[{x0:.0f},{x1:.0f}] y[{y0:.0f},{y1:.0f}] z[{z0:.1f},{z1:.1f}]")
        print(lineout, flush=True)
        out.write(lineout + "\n")
        for r in range(min(3, run)):
            x, y, z = xs[r]
            nm = h2n.get(struct.unpack_from("<I", mem, runstart + r * stride + bho)[0], "?")
            print(f"     ({x:10.2f},{y:10.2f},{z:8.2f})  {nm}", flush=True)
out.close()
print(f"findentities3: {hits} named entity arrays in {scanned} blobs")
