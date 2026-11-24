"""Dump the raw record bytes for far-away class-S hits, to see whether the frame is right there.

Finds records in a resource whose float triple at +0x00 equals a chosen far position, prints the
whole 80 bytes as 20 dwords with float/int interpretation, and the same 80 bytes at -0x40 and +0x40
so a shifted frame (OBB / other family) is obvious.

usage: python -I dumpfar.py <levels.rpf> <resource_hex> <n_records>
"""
import struct
import sys
import zlib

lv, res, want = sys.argv[1], sys.argv[2], int(sys.argv[3])
off = int(res, 16)
with open(lv, "rb") as f:
    f.seek(off)
    blob = zlib.decompressobj().decompress(f.read(2_000_000))

found = []
i = 0x90
while i + 0x70 <= len(blob):
    x, y, z = struct.unpack_from("<3f", blob, i)
    if max(abs(x), abs(y)) > 15000:
        found.append(i)
    i += 80
print(f"resource 0x{off:X} blob {len(blob):,} far records {len(found)} at {[hex(v) for v in found[:8]]}")


def show(base):
    for k in range(0, 0x50, 4):
        w = struct.unpack_from("<I", blob, base + k)
        fl = struct.unpack_from("<f", blob, base + k)
        print(f"   +{k:02x} {w[0]:08X} f={fl[0]:>14.6g}")


for b in found[:want]:
    print(f"\n=== record at +0x{b:X} (pos frame) ===")
    show(b)
    print("  -- 0x40 earlier --")
    show(b - 0x40)
    print("  -- 0x40 later --")
    show(b + 0x40)
