"""P9: where do the four pointer kinds point?

For a file whose array sits at absolute resource offset O, a pointer to the start of
record k has delta == O + k*0x88, i.e. delta mod 0x88 == O mod 0x88 for ALL such
pointers.  So per (file, slot) the modal value of delta mod 0x88 either equals the
array phase (points at a record) or not (points at something else).
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
REC = 0x88
SLOTS = {0x28: "A", 0x50: "B", 0x58: "C", 0x60: "D"}
out = []
w = out.append

def ptrs(b):
    n = len(b) // 8
    u = struct.unpack_from("<%dQ" % n, b, 0)
    return [(i * 8, q - P_LO) for i, q in enumerate(u) if 0 < q <= 0xFFFFFFFF and P_LO <= q <= P_HI]

grand = collections.Counter()
for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    w("=" * 90)
    w("FAMILY %s : delta mod 0x88 per pointer slot" % tag)
    w("  %-40s %9s | %-28s" % ("file", "n", "slot: modal residue (share)"))
    for name, p in files:
        b = L.load(p)
        ps = ptrs(b)
        if not ps:
            continue
        per = {}
        for off, d in ps:
            r = off % REC
            lab = SLOTS.get(r)
            if lab is None:
                continue
            per.setdefault(lab, collections.Counter())[d % REC] += 1
        bits = []
        for lab in "ABCD":
            c = per.get(lab)
            if not c:
                bits.append("%s:-" % lab); continue
            m, k = c.most_common(1)[0]
            n = sum(c.values())
            bits.append("%s:%02X(%.0f%%,n=%d)" % (lab, m, 100.0 * k / n, n))
            grand[(lab, k == n)] += 1
        w("  %-40s %9d | %s" % (name, len(ps), "  ".join(bits)))
    w("")
    w("files where the slot's pointers ALL share one residue: " +
      ", ".join("%s=%d" % (lab, grand[(lab, True)]) for lab in "ABCD"))
open("p9.out", "w").write("\n".join(out))
print("\n".join(out))
