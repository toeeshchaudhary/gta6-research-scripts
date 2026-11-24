"""Find occurrences of specific u32 hashes inside inflated resources and dump context.

Used to locate the archetype -> drawable binding record by its shape: if the archetype hash
appears next to a 0x5xxxxxxx/0x6xxxxxxx resource pointer (or an element index array), the
record layout is readable from the context dump.

Usage: python -I hashfind.py <archive> <candlist> <hexhash,...> <out.txt> [--max N] [--ctx 48]
"""
import argparse
import mmap
import struct
import sys
import zlib

POINTERS = range(0x50000000, 0x70000000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("cand")
    ap.add_argument("hashes")
    ap.add_argument("out")
    ap.add_argument("--max", type=int, default=40000)
    ap.add_argument("--ctx", type=int, default=48)
    ap.add_argument("--cap", type=int, default=1 << 21)
    a = ap.parse_args()
    want = {}
    for x in a.hashes.split(","):
        x = x.strip()
        if x:
            want[int(x, 16)] = 0

    offs = []
    with open(a.cand, "r", encoding="ascii", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    offs.append(int(ln.split("\t")[0], 16))
                except ValueError:
                    pass
    offs = offs[: a.max]

    fs = open(a.archive, "rb")
    mm = mmap.mmap(fs.fileno(), 0, access=mmap.ACCESS_READ)
    nres = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for off in offs:
            try:
                out = zlib.decompressobj().decompress(mm[off: off + (1 << 20)], a.cap)
            except zlib.error:
                continue
            if len(out) < 512:
                continue
            nres += 1
            n = len(out)
            found = False
            for hv in want:
                pat = struct.pack("<I", hv)
                i = out.find(pat)
                while i >= 0:
                    if i % 4 == 0:
                        s = max(0, i - a.ctx)
                        e = min(n, i + a.ctx)
                        seg = out[s:e]
                        ptrs = []
                        for q in range(0, len(seg) - 7, 4):
                            if (s + q) % 8:
                                continue
                            pv = struct.unpack_from("<Q", seg, q)[0]
                            if pv in POINTERS:
                                ptrs.append(f"@0x{s + q:X}:0x{pv:X}")
                        if not found:
                            f.write(f"\nRES 0x{off:X} size={n}\n")
                            found = True
                        want[hv] += 1
                        f.write(f"  0x{hv:08X} @0x{i:X} ptrs=[{' '.join(ptrs)}]\n")
                        for r in range(s, e, 16):
                            row = out[r:min(e, r + 16)]
                            hx = " ".join(f"{c:02X}" for c in row)
                            asc = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
                            f.write(f"    {r:06X}  {hx:<47}  {asc}\n")
                    i = out.find(pat, i + 1)
    mm.close()
    fs.close()
    print(f"resources scanned {nres}")
    for hv, c in want.items():
        print(f"0x{hv:08X}: {c} occurrences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
