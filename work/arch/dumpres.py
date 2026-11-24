"""Dump an inflated resource at a given archive offset: hex + printable, so record layouts can be
read off the bytes.

Usage: python -I dumpres.py <archive> <hexoff> [--len 2048] [--start 0] [--ascii]
"""
import argparse
import mmap
import struct
import sys
import zlib


def dump(b, start, n):
    for i in range(start, min(len(b), start + n), 16):
        row = b[i:i + 16]
        hx = " ".join(f"{c:02X}" for c in row)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
        print(f"{i:06X}  {hx:<47}  {asc}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("off")
    ap.add_argument("--len", type=int, default=2048)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--ascii", action="store_true")
    ap.add_argument("--cap", type=int, default=1 << 22)
    a = ap.parse_args()
    off = int(a.off, 16)
    fs = open(a.archive, "rb")
    mm = mmap.mmap(fs.fileno(), 0, access=mmap.ACCESS_READ)
    d = zlib.decompressobj()
    out = d.decompress(mm[off: off + (1 << 20)], a.cap)
    print(f"# res 0x{off:X} inflated {len(out)} bytes")
    dump(out, a.start, a.len)
    if a.ascii:
        print("--- strings ---")
        import re
        for m in re.finditer(rb"[\x21-\x7e]{4,200}", out):
            print(f"{m.start():06X} {m.group(0).decode('latin-1')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
