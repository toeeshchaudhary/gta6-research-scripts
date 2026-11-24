"""Task 4: structural analysis of the recovered program plaintext (the 26 exact zlib decodes).

Measures: alignment, pointer-word population (0x50xxxxxx), sentinel/flags, ascending u32 runs,
zero-run lengths, field-periodicity over candidate strides, and duplicates.
"""
import os, sys, struct, collections

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(B, "work", "codec", "full", "exact")

def u32s(b):
    n = len(b) // 4 * 4
    return list(struct.unpack_from("<%dI" % (n // 4), b, 0))

def analyse(path):
    b = open(path, "rb").read()
    w = u32s(b)
    L = len(w)
    print(f"\n== {os.path.basename(path)}  {len(b):,} B, {L:,} u32")
    print("   head64:", b[:64].hex())
    c = collections.Counter(w)
    print("   top words:", [(hex(k), v) for k, v in c.most_common(8)])
    ptr = [i for i, v in enumerate(w) if 0x50000000 <= v <= 0x50FFFFFF]
    print(f"   0x50xxxxxx words: {len(ptr)} ({100*len(ptr)/max(1,L):.2f}%)")
    for name, test in (("FFFFFFFF", 0xFFFFFFFF), ("00800000", 0x00800000), ("0000FFFF", 0xFFFF),
                       ("zero", 0)):
        n = c.get(test, 0)
        print(f"   {name:9s}: {n} ({100*n/max(1,L):.2f}%)")
    # ascending runs
    best = 1; cur = 1; asc_total = 0
    for i in range(1, L):
        if w[i] == w[i - 1] + 1: cur += 1
        else:
            if cur >= 4: asc_total += cur
            best = max(best, cur); cur = 1
    print(f"   longest strictly-ascending u32 run: {best}; u32 words inside runs>=4: {asc_total}")
    # zero runs
    zr = collections.Counter(); run = 0
    for v in w:
        if v == 0: run += 1
        elif run: zr[run] += 1; run = 0
    print(f"   zero runs: {sum(zr.values())} runs, max {max(zr) if zr else 0}, "
          f"runs>=8: {sum(v for k, v in zr.items() if k >= 8)}")
    # stride periodicity: for stride s, fraction of positions whose value-equal-class repeats
    print("   stride scan (score = frac of slots whose value is 0 or FFFFFFFF, best strides):")
    scores = []
    for s in (8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64):
        hit = tot = 0
        for off in range(0, 32):
            for i in range(off, L - s, s):
                tot += 1
                if w[i] in (0, 0xFFFFFFFF, 0x00800000): hit += 1
        scores.append((hit / max(1, tot), s))
    for sc, s in sorted(scores, reverse=True)[:5]:
        print(f"      stride {s:3d}: {sc:.3f}")
    # duplicates of any 8-byte pair
    pairs = collections.Counter((w[i], w[i + 1]) for i in range(0, L - 1, 2))
    dp = [p for p, n in pairs.items() if n > 1 and p != (0, 0)]
    print(f"   duplicated aligned 8-byte pairs: {len(dp)} (top {sorted(pairs.values())[-3:] if pairs else ''})")
    return b, w

def main():
    for fn in sorted(os.listdir(D)):
        analyse(os.path.join(D, fn))
    return 0

if __name__ == "__main__":
    sys.exit(main())
