"""P8: the 0x88 record.  Verify the pointer-slot hypothesis exactly, then build the
per-field (17 x u64) profile of the record across both families.
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
REC = 0x88
POFF = (0x28, 0x50, 0x58, 0x60)
out = []
w = out.append

def strict_ptrs(b):
    n = len(b) // 8
    u = struct.unpack_from("<%dQ" % n, b, 0)
    return [(i * 8, q - P_LO) for i, q in enumerate(u) if 0 < q <= 0xFFFFFFFF and P_LO <= q <= P_HI]

for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    w("=" * 88)
    w("FAMILY %s" % tag)
    hit = 0; tot = 0; byslot = collections.Counter(); misaligned = []
    for name, p in files:
        b = L.load(p)
        for off, d in strict_ptrs(b):
            tot += 1
            r = off % REC
            if r in POFF:
                hit += 1
                byslot[r] += 1
            elif len(misaligned) < 12:
                misaligned.append((name, off, r))
    w("strict pointers landing on record-relative slot {0x28,0x50,0x58,0x60}: %d/%d = %.2f%%"
      % (hit, tot, 100.0 * hit / tot))
    w("   by slot: " + ", ".join("+%02X:%d" % (k, byslot[k]) for k in sorted(byslot)))
    w("   first off-pattern examples: " + str(misaligned))
    w("")
    # field profile over 17 u64 fields
    cnt = collections.Counter(); nrec = 0
    small = collections.Counter(); ptrc = collections.Counter()
    for name, p in files:
        b = L.load(p)
        n = len(b) // REC
        for k in range(n):
            base = k * REC
            nrec += 1
            for f in range(17):
                q = struct.unpack_from("<Q", b, base + f * 8)[0]
                cnt[(f, "zero")] += (q == 0)
                cnt[(f, "sent")] += (q == 0xFFFFFFFFFFFFFFFF or q == 0x00000000FFFFFFFF)
                cnt[(f, "ptr")] += (P_LO <= q <= P_HI)
                cnt[(f, "small")] += (0 < q < 0x10000)
                cnt[(f, "u32hi0")] += (0 < q <= 0xFFFFFFFF and q >= 0x10000)
    w("%d records of 0x%X B; per-field profile (percent of records):" % (nrec, REC))
    w("  field  off    zero%%  sent%%  ptr%%  small%%  hi0%%")
    for f in range(17):
        w("   %2d   +%02X   %5.1f  %5.1f  %5.1f  %6.1f  %5.1f" % (
            f, f * 8,
            100.0 * cnt[(f, "zero")] / nrec,
            100.0 * cnt[(f, "sent")] / nrec,
            100.0 * cnt[(f, "ptr")] / nrec,
            100.0 * cnt[(f, "small")] / nrec,
            100.0 * cnt[(f, "u32hi0")] / nrec))
open("p8.out", "w").write("\n".join(out))
print("\n".join(out))
