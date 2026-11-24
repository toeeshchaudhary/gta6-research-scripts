"""Harvest name-shaped strings from inflated RAGE resource blobs at candidate offsets.

Candidate offsets come from the existing verified page-scan lists (work/world/cand_*.txt).
Strings are collected from the *decompressed* system+graphics blocks of every resource, so
what we get is resource-internal identifier text (drawable names, bone names, archetype
names), not archive noise.

Usage: python -I harvest.py <archive> <candlist> <out.txt> [--max N] [--cap 262144]
"""
import argparse
import mmap
import re
import sys
import zlib

# printable, no spaces/NUL: RAGE name strings are identifier-shaped
STR = re.compile(rb"[\x21-\x7e]{3,190}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("cand")
    ap.add_argument("out")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--cap", type=int, default=262144)
    ap.add_argument("--win", type=int, default=1 << 20)
    a = ap.parse_args()

    offs = []
    with open(a.cand, "r", encoding="ascii", errors="ignore") as f:
        for ln in f:
            ln = ln.strip().split("\t")[0].split(",")[0]
            if not ln:
                continue
            try:
                offs.append(int(ln, 16))
            except ValueError:
                pass
    if a.max:
        offs = offs[: a.max]
    print(f"{a.archive}: {len(offs)} candidates", flush=True)

    strings = set()
    ok = bad = 0
    fs = open(a.archive, "rb")
    mm = mmap.mmap(fs.fileno(), 0, access=mmap.ACCESS_READ)
    mlen = len(mm)
    for i, off in enumerate(offs):
        if off + 8 >= mlen:
            continue
        chunk = mm[off: off + a.win]
        try:
            d = zlib.decompressobj()
            out = d.decompress(chunk, a.cap)
        except zlib.error:
            bad += 1
            continue
        if len(out) < 64:
            bad += 1
            continue
        ok += 1
        for m in STR.finditer(out):
            strings.add(m.group(0).decode("latin-1"))
        if (i + 1) % 20000 == 0:
            print(f"  {i + 1}/{len(offs)} ok={ok} bad={bad} strings={len(strings)}", flush=True)
    mm.close()
    fs.close()

    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for s in sorted(strings):
            f.write(s + "\n")
    print(f"{a.out}: {len(strings)} strings from {ok} inflated blobs (bad={bad})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
