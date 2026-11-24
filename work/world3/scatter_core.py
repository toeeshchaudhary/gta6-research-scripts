"""Top-down scatter of WORLD-SPACE class-S instances, framed on the dense core (2-98 percentile).

usage: python -I scatter_core.py <scene.json> <out.png> [size] [class]
"""
import json
import struct
import sys
import zlib

src, dst = sys.argv[1], sys.argv[2]
SIZE = int(sys.argv[3]) if len(sys.argv) > 3 else 1800
KEEP = sys.argv[4] if len(sys.argv) > 4 else "S"

recs = json.load(open(src, encoding="utf-8"))["instances"]
if "class" in (recs[0] if recs else {}):
    recs = [r for r in recs if r.get("class") == KEEP]
print(f"instances ({KEEP}): {len(recs):,}")
xs = [r["pos"][0] for r in recs]
ys = [r["pos"][1] for r in recs]
zs = [r["pos"][2] for r in recs]


def pct(a, q):
    b = sorted(a)
    return b[int(q * (len(b) - 1))]


x0, x1 = pct(xs, 0.02), pct(xs, 0.98)
y0, y1 = pct(ys, 0.02), pct(ys, 0.98)
z0, z1 = pct(zs, 0.02), pct(zs, 0.98)
print(f"core frame x[{x0:.0f},{x1:.0f}] y[{y0:.0f},{y1:.0f}] z[{z0:.1f},{z1:.1f}]")

W = H = SIZE
pad = 24
s = min((W - 2 * pad) / (x1 - x0), (H - 2 * pad) / (y1 - y0))
img = bytearray(W * H * 3)
for i in range(W * H):
    img[i * 3], img[i * 3 + 1], img[i * 3 + 2] = 8, 9, 16

n = inside = 0
for r in recs:
    x, y, z = r["pos"]
    n += 1
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        continue
    inside += 1
    px = int(pad + (x - x0) * s)
    py = int(pad + (y1 - y) * s)
    t = max(0.0, min(1.0, (z - z0) / max(1e-6, z1 - z0)))
    rr = int(40 + 215 * t)
    gg = int(150 + 90 * (1 - abs(t - 0.55) / 0.55)) if abs(t - 0.55) < 0.55 else 150
    gg = max(0, min(255, gg))
    bb = int(255 - 200 * t)
    for dy in (0, 1):
        for dx in (0, 1):
            X, Y = px + dx, py + dy
            if 0 <= X < W and 0 <= Y < H:
                o = (Y * W + X) * 3
                img[o] = max(img[o], rr)
                img[o + 1] = max(img[o + 1], gg)
                img[o + 2] = max(img[o + 2], bb)
print(f"plotted {inside:,} of {n:,} ({100*inside/n:.1f}% inside the core frame)")


def chunk(t, d):
    c = t + d
    return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)


raw = b"".join(b"\x00" + bytes(img[y * W * 3:(y + 1) * W * 3]) for y in range(H))
png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) +
       chunk(b"tEXt", f"Title\x00WORLD3 class-{KEEP} instances, core frame 2-98pct".encode()) +
       chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
open(dst, "wb").write(png)
print(f"wrote {dst} ({len(png):,} bytes)")
