"""Measure dictionary resolution over a scene's distinct archetype hashes.

Usage: python -I measure.py <dict.tsv> <hashfreq.tsv> [--top 25]
Reports: distinct hashes, resolved, resolved instances, top unresolved with frequency.
"""
import sys
from collections import Counter


def main():
    dictp, hp = sys.argv[1], sys.argv[2]
    top = 25
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])

    d = {}
    with open(dictp, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            p = ln.rstrip("\r\n").split("\t")
            if len(p) >= 2:
                d[int(p[0], 16)] = p[1]

    tot_i = tot_h = res_h = res_i = 0
    un = []
    with open(hp, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            p = ln.split()
            if len(p) < 2:
                continue
            h = int(p[0], 16)
            n = int(p[1])
            tot_h += 1
            tot_i += n
            if h in d:
                res_h += 1
                res_i += n
            else:
                un.append((h, n))
    un.sort(key=lambda x: -x[1])
    print(f"distinct hashes      {tot_h}")
    print(f"instances            {tot_i}")
    print(f"resolved hashes      {res_h}  ({100.0 * res_h / max(tot_h, 1):.2f}%)")
    print(f"resolved instances   {res_i}  ({100.0 * res_i / max(tot_i, 1):.2f}%)")
    print(f"unresolved hashes    {len(un)}")
    print("top unresolved by instance frequency:")
    for h, n in un[:top]:
        print(f"  0x{h:08X}\t{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
