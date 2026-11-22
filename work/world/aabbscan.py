"""Find world-space AABB records in resource headers = streaming block / cell descriptors.

Checks every 4-byte offset in the first 4 KiB of each inflated system blob for a
(min.xyz, max.xyz) float3 pair (12 or 16 bytes apart) with min < max on all axes.
Reports blobs whose extents are large (world-scale).

usage: python -I aabbscan.py <archive> <candidates.txt> [maxBlobs] [minExtent]
"""
import struct
import sys
import zlib

arch, candfile = sys.argv[1], sys.argv[2]
maxblobs = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
minext = float(sys.argv[4]) if len(sys.argv) > 4 else 200.0


def f32(mem, o):
    return struct.unpack_from("<f", mem, o)[0]


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
            mem = zlib.decompressobj().decompress(f.read(1 << 18))
        except Exception:
            continue
        scanned += 1
        if len(mem) < 128:
            continue
        best = None
        for o in range(0, min(len(mem) - 96, 4096), 4):
            for gap in (12, 16):
                a = [f32(mem, o + 4 * i) for i in range(3)]
                b = [f32(mem, o + gap + 4 * i) for i in range(3)]
                if not all(abs(v) < 20000 for v in a + b):
                    continue
                if not all(b[i] > a[i] for i in range(3)):
                    continue
                ext = max(b[i] - a[i] for i in range(3))
                if ext < minext:
                    continue
                if best is None or ext > best[0]:
                    best = (ext, o, gap, a, b)
        if best is None:
            continue
        hits += 1
        ext, o, gap, a, b = best
        print(f"0x{off:X} len={len(mem):,} aabb@{o} gap={gap} ext={ext:.0f} "
              f"min=({a[0]:.1f},{a[1]:.1f},{a[2]:.1f}) max=({b[0]:.1f},{b[1]:.1f},{b[2]:.1f})")
print(f"aabbscan: {hits} world-extent headers in {scanned} blobs")
