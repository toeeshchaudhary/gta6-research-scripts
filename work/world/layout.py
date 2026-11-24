"""Discover the record layout of a resource by finding the (stride, start, field) that makes
archetype-name hashes resolve against a joaat name set. Then decode positions.

usage: python -I layout.py <archive> <offsetHex> <names.tsv> [minResolveFrac]
"""
import collections
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


arch, off, namefile = sys.argv[1], int(sys.argv[2], 16), sys.argv[3]
minfrac = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5

h2n = {}
for line in open(namefile, encoding="utf-8", errors="replace"):
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 2:
        continue
    n = parts[1]
    for cand in (n, n.split(".")[0], n.replace(".#ft", "")):
        if cand:
            h2n.setdefault(joaat(cand), cand)

with open(arch, "rb", buffering=0) as f:
    f.seek(off)
    d = zlib.decompressobj()
    mem = bytearray()
    while not d.eof:
        chunk = f.read(1 << 20)
        if not chunk:
            break
        mem += d.decompress(chunk, 64 << 20)
mem = bytes(mem)
print(f"blob 0x{off:X} inflated {len(mem):,} bytes   name hashes {len(h2n):,}")

best = []
for stride in range(24, 260, 4):
    w = stride // 4
    for start in range(0, min(stride, 32), 4):
        records = (len(mem) - start) // stride
        if records < 12:
            continue
        for f in range(w):
            total = 0
            good = 0
            distinct = set()
            for r in range(records):
                o = start + r * stride + f * 4
                if o + 4 > len(mem):
                    break
                v = struct.unpack_from("<I", mem, o)[0]
                total += 1
                if v in h2n:
                    good += 1
                    distinct.add(v)
            if total < 12:
                continue
            frac = good / total
            if frac >= minfrac and good >= 8:
                best.append((good, frac, distinct, stride, start, f, total))

best.sort(key=lambda x: (-x[0], -x[1]))
print(f"candidate layouts: {len(best)}")
seen = set()
for good, frac, distinct, stride, start, f, total in best[:200]:
    key = (stride, f)
    if key in seen:
        continue
    seen.add(key)
    print(f"  stride={stride:3} start={start:2} field=+{f*4:3} resolved={good:5}/{total:<6} "
          f"frac={frac:5.2f} distinct={len(distinct)}")
    if len(seen) >= 8:
        break

if not best:
    sys.exit(0)

good, frac, distinct, stride, start, f, total = best[0]
print(f"\n--- decoding array stride={stride} start={start} hashField=+{f*4} ---")
counts = collections.Counter()
examples = 0
for r in range(min(total, 400)):
    o = start + r * stride
    v = struct.unpack_from("<I", mem, o + f * 4)[0]
    name = h2n.get(v)
    if name:
        counts[name] += 1
    if name and examples < 10:
        examples += 1
        print(f"rec {r:4}@{o:06X}  {name}")
        for row in range(o, min(len(mem) - 16, o + stride), 16):
            w4 = struct.unpack_from("<4I", mem, row)
            fl = struct.unpack_from("<4f", mem, row)
            print(f"    {row:06X}  " + " ".join(f"{x:08X}" for x in w4) + "   " +
                  " ".join(f"{x:+10.4g}" for x in fl))
print("\ntop archetypes:", counts.most_common(10))
