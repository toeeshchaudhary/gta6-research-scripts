"""P12: is the 0x5xxxxxxx space SHARED across files?
(a) repeated deltas: how many distinct files reference the same absolute offset?
(b) per-file, per-slot delta ranges: do different files' target ranges overlap?
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
REC = 0x88
SLOTS = {0x28: "A", 0x50: "B", 0x58: "C", 0x60: "D"}
out = []
w = out.append

def per_file(files):
    res = {}
    for name, p in files:
        b = L.load(p)
        n = len(b) // 8
        u = struct.unpack_from("<%dQ" % n, b, 0)
        d = collections.defaultdict(list)
        for i, q in enumerate(u):
            if 0 < q <= 0xFFFFFFFF and P_LO <= q <= P_HI:
                lab = SLOTS.get((i * 8) % REC)
                if lab:
                    d[lab].append(q - P_LO)
        res[name] = d
    return res

for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    r = per_file(files)
    w("=" * 90)
    w("FAMILY %s" % tag)
    # (a) delta -> set of files
    byd = collections.defaultdict(set)
    for name, d in r.items():
        for lab, ds in d.items():
            for x in ds:
                byd[x].add(name)
    multi = [(x, len(s)) for x, s in byd.items() if len(s) > 1]
    multi.sort(key=lambda t: -t[1])
    w("deltas referenced from >1 file: %d of %d distinct" % (len(multi), len(byd)))
    for x, k in multi[:15]:
        w("   +%06X  in %d files: %s" % (x, k, ", ".join(sorted(byd[x])[:4])))
    w("")
    # (b) ranges
    w("per-file per-slot delta range (hex):")
    for name, d in r.items():
        bits = []
        for lab in "ACD":
            ds = d.get(lab) or [0]
            bits.append("%s %06X..%06X" % (lab, min(ds), max(ds)))
        w("  %-42s %s" % (name[:42], "  ".join(bits)))
open("p12.out", "w").write("\n".join(out))
print("\n".join(out[:60]))
