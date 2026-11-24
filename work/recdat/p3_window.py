"""P3: three decisive experiments.
(a) alignment residues mod 16 / mod 4
(b) WINDOW TEST: is each file a contiguous fragment resource[O:O+size]?
    (for every observed delta O, count deltas inside [O,O+size))
(c) CONTEXT of the recurring deltas: where do they appear, what surrounds them
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
out = []
w = out.append

def ptrs(b):
    d = L.u32s(b)
    return [(i * 4, v - P_LO) for i, v in enumerate(d) if P_LO <= v <= P_HI]

for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    w("=" * 78)
    w("FAMILY %s" % tag)
    mod16 = collections.Counter(); mod4 = collections.Counter(); n = 0
    win_results = []
    for name, p in files:
        b = L.load(p)
        ds = [d for _, d in ptrs(b)]
        if not ds:
            continue
        n += len(ds)
        for d in ds:
            mod16[d % 16] += 1
            mod4[d % 4] += 1
        # window test
        best = (0, 0)
        for O in set(ds):
            c = sum(1 for d in ds if O <= d < O + len(b))
            if c > best[1]:
                best = (O, c)
        win_results.append((name, len(b), len(ds), best[0], best[1]))
    w("delta mod 16 histogram (n=%d):" % n)
    for k in range(16):
        w("   %2d : %6d  %5.1f%% %s" % (k, mod16[k], 100.0 * mod16[k] / n, "#" * int(60.0 * mod16[k] / max(mod16.values()))))
    w("delta mod 4: " + ", ".join("%d:%d" % (k, mod4[k]) for k in range(4)))
    w("")
    w("WINDOW TEST  (deltas inside one window of the file's own size)")
    w("  %-40s %7s %5s %9s %5s %6s" % ("file", "size", "nptr", "bestO", "inwin", "share"))
    tot = 0; totin = 0
    for name, sz, nds, O, c in win_results:
        tot += nds; totin += c
        w("  %-40s %7d %5d %9X %5d %5.1f%%" % (name, sz, nds, O, c, 100.0 * c / nds))
    w("  TOTAL: %d/%d = %.1f%% of pointers fall inside a single file-sized window" % (totin, tot, 100.0 * totin / tot))
    w("")

w("=" * 78)
w("CONTEXT OF RECURRING DELTAS (family A)")
A = L.fam_a()
target = [0x06FF20, 0x06F220, 0x01FF30, 0x02D7B0, 0x02345  ]
occ = collections.defaultdict(list)   # delta -> [(file, fileoff)]
for name, p in A:
    b = L.load(p)
    for off, d in ptrs(b):
        occ[d].append((name, off))
for d in target:
    if d is None: continue
    lst = occ.get(d, [])
    w("")
    w("delta +%06X  (value 0x%08X)  occurrences=%d  files=%d" % (d, 0x50000000 + d, len(lst), len(set(x[0] for x in lst))))
    for name, off in lst[:4]:
        b = L.load(dict(A)[name])
        ctr = max(0, off - 16)
        w("  -- %s @ file+%06X" % (name, off))
        w(L.hexdump(b, ctr, 16, 64))

open("p3.out", "w").write("\n".join(out))
print("\n".join(out[:40]))
