"""P5: head census.  Group files by the shape of their first 48 bytes."""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
out = []
w = out.append

def kind(v):
    if v == 0: return "0"
    if v == 0xFFFFFFFF: return "S"
    if P_LO <= v <= P_HI: return "P"
    if 0 < v < 0x10000: return "s"      # small
    return "?"

for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    w("=" * 100)
    w("FAMILY %s  head census" % tag)
    for name, p in files:
        b = L.load(p)
        d = L.u32s(b)
        k = "".join(kind(v) for v in d[:12])
        w("%-42s %7d  %s   %s" % (name, len(b), k,
                                  " ".join("%08X" % v for v in d[:6])))
open("p5.out", "w").write("\n".join(out))
print("\n".join(out))
