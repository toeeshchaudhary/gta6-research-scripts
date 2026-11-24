"""P13: P-class (permutation-header) files.
(a) rigorous test: is the head a permutation of 0..N-1 read as LE u16 at byte phase 0 or 1?
(b) ascending u32 runs (index/offset tables) - span, length, step
(c) high-entropy 4-byte token vocabulary - is it a small repeating dictionary?
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
out = []
w = out.append

def permtest(b):
    best = None
    for ph in (0, 1, 2, 3):
        vals = []
        for k in range(16):
            o = ph + 2 * k
            if o + 2 > len(b):
                break
            vals.append(struct.unpack_from("<H", b, o)[0])
        for n in range(2, 13):
            v = vals[:n]
            if sorted(v) == list(range(n)):
                if best is None or n > best[1]:
                    best = (ph, n, v)
    return best

def u32runs(b, minlen=4, maxval=0x100000):
    d = [struct.unpack_from("<I", b, i * 4)[0] for i in range(len(b) // 4)]
    runs = []
    i = 0
    while i < len(d) - minlen:
        j = i
        while j + 1 < len(d) and d[j + 1] > d[j] and d[j + 1] < maxval:
            j += 1
        if j - i + 1 >= minlen:
            runs.append((i * 4, j - i + 1, d[i], d[j]))
            i = j + 1
        else:
            i += 1
    return runs

def tokens(b, lo=0x1000000):
    """4-byte values that are not pointers, not small ints - candidate hash constants"""
    c = collections.Counter()
    for i in range(len(b) // 4):
        v = struct.unpack_from("<I", b, i * 4)[0]
        if lo <= v <= 0xFFF00000 and not (P_LO <= v <= P_HI):
            c[v] += 1
    return c

for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    w("=" * 96)
    w("FAMILY %s : permutation headers, u32 tables, token vocabulary" % tag)
    for name, p in files:
        b = L.load(p)
        pm = permtest(b)
        runs = u32runs(b)
        tc = tokens(b)
        tot_runs = sum(r[1] for r in runs)
        w("%-42s %6d  perm=%s  runs=%2d(%d dwords)  tok=%d distinct, top=%s" % (
            name[:42], len(b),
            ("phase%d n=%d" % (pm[0], pm[1])) if pm else "-    ",
            len(runs), tot_runs, len(tc),
            ", ".join("%08X x%d" % (v, k) for v, k in tc.most_common(3)) if tc else "-"))
open("p13.out", "w").write("\n".join(out))
print("\n".join(out))
