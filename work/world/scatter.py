"""Top-down scatter plot of instance positions, written as a PNG with no third-party libs.

Colour by height (blue = low, red = high); brighter/denser where instances cluster.
usage: python -I scatter.py <instances.json> <out.png> [size] [title]
"""
import json
import struct
import sys
import zlib

src, dst = sys.argv[1], sys.argv[2]
SIZE = int(sys.argv[3]) if len(sys.argv) > 3 else 1600

doc = json.load(open(src, encoding="utf-8"))
pts = [(i["pos"][0], i["pos"][1], i["pos"][2]) for i in doc["instances"]]
print(f"instances: {len(pts)}")
if not pts:
    raise SystemExit("no points")

# robust bounds (1st..99th percentile) so outliers do not squash the plot
xs = sorted(p[0] for p in pts)
ys = sorted(p[1] for p in pts)
zs = sorted(p[2] for p in pts)
lo = lambda a: a[int(len(a) * 0.005)]
hi = lambda a: a[min(len(a) - 1, int(len(a) * 0.995))]
x0, x1 = lo(xs), hi(xs)
y0, y1 = lo(ys), hi(ys)
z0, z1 = lo(zs), hi(zs)
if x1 - x0 < 1e-6:
    x1 = x0 + 1
if y1 - y0 < 1e-6:
    y1 = y0 + 1
if z1 - z0 < 1e-6:
    z1 = z0 + 1
print(f"x[{x0:.1f},{x1:.1f}] y[{y0:.1f},{y1:.1f}] z[{z0:.1f},{z1:.1f}]")

W = H = SIZE
buf = bytearray(W * H * 3)
# background: dark slate
for i in range(W * H):
    buf[i * 3] = 18
    buf[i * 3 + 1] = 20
    buf[i * 3 + 2] = 26

counts = {}
for (x, y, z) in pts:
    px = int((x - x0) / (x1 - x0) * (W - 1))
    py = int((y1 - y) / (y1 - y0) * (H - 1))
    if not (0 <= px < W and 0 <= py < H):
        continue
    t = (z - z0) / (z1 - z0)
    r = int(255 * min(1.0, max(0.0, 1.6 * t)))
    g = int(255 * min(1.0, max(0.0, 0.9 - abs(t - 0.5) * 1.6)))
    b = int(255 * min(1.0, max(0.0, 1.4 * (1.0 - t))))
    key = py * W + px
    counts[key] = counts.get(key, 0) + 1
    k = key * 3
    buf[k] = max(buf[k], r)
    buf[k + 1] = max(buf[k + 1], g)
    buf[k + 2] = max(buf[k + 2], b)

# raw PNG: 8-bit RGB, filter byte 0 per scanline
raw = bytearray()
for row in range(H):
    raw.append(0)
    raw += buf[row * W * 3:(row + 1) * W * 3]


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


png = (b"\x89PNG\r\n\x1a\n" +
       chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) +
       chunk(b"tEXt", b"Title\x00Top-down scatter of GTA VI entity instances") +
       chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
       chunk(b"IEND", b""))
open(dst, "wb").write(png)
print(f"wrote {dst} ({len(png):,} bytes), {len(counts):,} occupied pixels")
