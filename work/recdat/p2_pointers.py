"""P2: pointer model with the CORRECT mask, per-file alignment residue, lane analysis.

LINEAGE.md 4.2: pointers are `0x50 << 24 | off`, mask & 0xFFFFFF, so the legal
pointer form is 0x50000000..0x50FFFFFF.  Anything else in 0x51..0x5F is NOT a pointer.
"""
import sys, struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF

def run(files, tag, out):
    w = out.append
    w("=" * 78)
    w("FAMILY %s : %d files" % (tag, len(files)))
    tot_dw = 0
    nptr = 0
    lane = collections.Counter()       # byte lane (offset%8) of the 0x50 byte
    parity = collections.Counter()     # dword index parity
    mod8 = collections.Counter()
    per = []
    alldelta = collections.Counter()
    for name, p in files:
        b = L.load(p)
        d = L.u32s(b)
        tot_dw += len(d)
        ds = []
        for i, v in enumerate(d):
            if P_LO <= v <= P_HI:
                nptr += 1
                ds.append(v - P_LO)
                alldelta[v - P_LO] += 1
                parity[i % 2] += 1
                off = i * 4
                for k in range(4):
                    if (v >> (8 * k)) & 0xFF == 0x50:
                        lane[(off + k) % 8] += 1
                        break
        m8 = collections.Counter(x % 8 for x in ds)
        mode = m8.most_common(1)[0] if m8 else (0, 0)
        per.append((name, len(b), len(ds), min(ds) if ds else 0, max(ds) if ds else 0,
                    mode[0], mode[1] / float(len(ds)) if ds else 0))
    w("dwords=%d  pointers=%d (%.1f per 1000 dwords)" % (tot_dw, nptr, 1000.0 * nptr / tot_dw))
    w("dword-index parity: even=%d odd=%d  (%.1f%% even)" % (parity[0], parity[1], 100.0 * parity[0] / nptr))
    w("byte lane of 0x50 inside an 8-byte record:")
    for k in sorted(lane):
        w("   lane %d: %6d  %.1f%%" % (k, lane[k], 100.0 * lane[k] / nptr))
    w("")
    w("per-file: modal delta%%8 residue = how the file's start sits inside the resource")
    w("  %-40s %7s %5s %9s %9s %4s %6s" % ("file", "size", "nptr", "min", "max", "mod", "share"))
    wsum = collections.Counter()
    for name, sz, n, mn, mx, m, sh in per:
        w("  %-40s %7d %5d %9X %9X %4d %6.1f%%" % (name, sz, n, mn, mx, m, 100 * sh))
        wsum[m] += sh
    w("")
    w("family-wide modal residues (weighted share per residue):")
    for k in sorted(wsum, key=lambda x: -wsum[x]):
        w("   residue %d  summed share %.2f" % (k, wsum[k]))
    w("")
    w("global delta census: distinct=%d  per-pointer=%.2f" % (len(alldelta), nptr / float(len(alldelta))))
    for d, c in alldelta.most_common(20):
        w("   +%06X  x%d" % (d, c))
    w("")
    # 0x5F5F... style non-masked false positives that the narrow mask drops
    return per

lines = []
A = L.fam_a(); B = L.fam_b()
run(A, "A", lines)
run(B, "B", lines)
open("p2.out", "w").write("\n".join(lines))
print("\n".join(lines[:30]))
print("... written to p2.out (%d lines)" % len(lines))
