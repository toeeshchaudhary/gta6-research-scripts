"""P4: interactive single-file walker.  Estimate the fragment base O, then annotate
every dword: pointer -> resident file offset (if inside), or 'EXT' if it leaves the fragment.
"""
import sys, struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF

def ptrs(b):
    d = L.u32s(b)
    return [(i * 4, v - P_LO) for i, v in enumerate(d) if P_LO <= v <= P_HI]

def estimate_O(b):
    ds = [d for _, d in ptrs(b)]
    nz = [d for d in ds if d]
    if not nz:
        return 0
    best = (nz[0], -1)
    for O in set(nz):
        c = sum(1 for d in nz if O <= d < O + len(b))
        if c > best[1] or (c == best[1] and O < best[0]):
            best = (O, c)
    return best[0]

def walk(name, path, start=0, nbytes=0x180, O=None):
    b = L.load(path)
    if O is None:
        O = estimate_O(b)
    print("### %s  size=%d  O=0x%X (fragment start)" % (name, len(b), O))
    d = L.u32s(b)
    for off in range(start, min(len(b), start + nbytes), 8):
        i = off // 4
        a, c = d[i], d[i + 1]
        desc = []
        for j, v in ((0, a), (1, c)):
            o = off + 4 * j
            if P_LO <= v <= P_HI:
                t = v - P_LO - O
                if 0 <= t < len(b):
                    desc.append("+%02X:PTR->%06X" % (j * 4, t))
                else:
                    desc.append("+%02X:PTR EXT %06X" % (j * 4, v - P_LO))
            elif v == 0xFFFFFFFF:
                desc.append("+%02X:SENT" % (j * 4))
            elif v == 0:
                desc.append("+%02X:0" % (j * 4))
        f2 = L.f32(a)
        print("%06X | %08X %08X | %-42s %6d %6d  %s" %
              (off, a, c, " ".join(desc), L.i32(a), L.i32(c),
               ("f=%.4g" % f2) if 1e-6 < abs(f2) < 1e7 else ""))

if __name__ == "__main__":
    A = dict(L.fam_a()); B = dict(L.fam_b())
    name = sys.argv[1]
    src = A if name in A else B
    O = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
    start = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
    n = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x180
    walk(name, src[name], start, n, O)
