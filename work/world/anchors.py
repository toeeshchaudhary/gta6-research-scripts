"""Anchor analysis: find resolved archetype hashes in a resource and decode the record around them.

usage: python -I anchors.py <archive> <offsetHex> <hashes.txt> <names.tsv>
"""
import collections
import re
import struct
import sys
import zlib


def joaat(s: str) -> int:
    h = 0
    for c in s.lower().encode("latin-1", "replace"):
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF


arch, offs, namefile = sys.argv[1], int(sys.argv[2], 16), sys.argv[3]
off = int(sys.argv[2], 16)

# name -> hash, so we can resolve
n2h = {}
for line in open(namefile, encoding="utf-8", errors="replace"):
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 2:
        continue
    n = parts[1]
    for cand in (n, n.split(".")[0], n.replace(".#ft", "")):
        if cand:
            n2h.setdefault(joaat(cand), cand)
h2n = {v: k for k, v in n2h.items()}
hset = set(n2h)

with open(arch, "rb", buffering=0) as f:
    f.seek(off)
    d = zlib.decompressobj()
    out = bytearray()
    while True:
        chunk = f.read(1 << 20)
        if not chunk:
            break
        out += d.decompress(chunk, 64 << 20)
        if d.eof or len(out) > (64 << 20):
            break
    try:
        out += d.flush()
    except Exception:
        pass

mem = bytes(out)
print(f"blob 0x{off:X} inflated {len(mem):,} bytes")

anchors = []
for o in range(0, len(mem) - 4, 4):
    v = struct.unpack_from("<I", mem, o)[0]
    if v in hset:
        anchors.append(o)
print(f"anchors (resolvable hashes): {len(anchors)}")

if len(anchors) > 3:
    deltas = collections.Counter(b - a for a, b in zip(anchors, anchors[1:]))
    print("top anchor deltas:", deltas.most_common(8))

# report the most common period and show record windows around anchors
if anchors:
    period = None
    if len(anchors) > 3:
        deltas = collections.Counter(b - a for a, b in zip(anchors, anchors[1:]))
        period = deltas.most_common(1)[0][0]
        print("dominant period:", period)
    for a in anchors[:6]:
        base = a - (a % 32 if period in (None, 32) else 0)
        print(f"\n--- anchor 0x{a:X} = {n2h[struct.unpack_from('<I', mem, a)[0]]}")
        for row in range(max(0, a - 32), min(len(mem) - 32, a + 32), 16):
            words = struct.unpack_from("<4I", mem, row)
            floats = struct.unpack_from("<4f", mem, row)
            print(f"  {row:06X}  " + " ".join(f"{w:08X}" for w in words) +
                  "   " + " ".join(f"{v:+.5g}" for v in floats))
