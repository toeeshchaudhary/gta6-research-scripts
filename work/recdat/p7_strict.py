"""P7: STRICT pointer model.

A RAGE pointer here is a 64-bit field: low dword = 0x50<<24 | off, high dword = 0.
Test how much the u64 view cleans the signal, and what alignment the true pointer
targets have.  Also: slot-class profile modulo the 34-dword (0x88) record period.
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
out = []
w = out.append

def strict_ptrs(b):
    """u64 slots where low dword is a 0x50xxxxxx value and high dword is 0."""
    n = len(b) // 8
    u = struct.unpack_from("<%dQ" % n, b, 0)
    res = []
    for i, q in enumerate(u):
        if 0 < q <= 0xFFFFFFFF and P_LO <= q <= P_HI:
            res.append((i * 8, q - P_LO))
    return res

for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    w("=" * 90)
    w("FAMILY %s  strict u64 pointer model" % tag)
    n = 0; mod = collections.Counter(); tot_dw = 0
    slotptr = collections.Counter(); slotzero = collections.Counter(); slotn = collections.Counter()
    files_with = 0
    for name, p in files:
        b = L.load(p)
        tot_dw += len(b) // 4
        sp = strict_ptrs(b)
        if sp:
            files_with += 1
        n += len(sp)
        for off, d in sp:
            mod[d % 16] += 1
        # slot profile mod 34 dwords (0x88 stride), phase-free
        d = L.u32s(b)
        for i, v in enumerate(d):
            k = i % 34
            slotn[k] += 1
            if P_LO <= v <= P_HI:
                slotptr[k] += 1
            if v == 0:
                slotzero[k] += 1
    w("strict pointers = %d in %d dwords (%.1f per 1000)  files with >=1: %d/%d"
      % (n, tot_dw, 1000.0 * n / tot_dw, files_with, len(files)))
    w("target delta mod 16:")
    for k in range(16):
        w("   %2d : %6d  %5.1f%%" % (k, mod[k], 100.0 * mod[k] / n))
    w("")
    w("slot profile modulo the 34-dword (0x88 byte) record period, family-wide:")
    w("  slot  ptr%%   zero%%")
    for k in range(34):
        w("   %2d   %5.1f  %5.1f" % (k, 100.0 * slotptr[k] / slotn[k], 100.0 * slotzero[k] / slotn[k]))
open("p7.out", "w").write("\n".join(out))
print("\n".join(out))
