"""P10: raw value lists per pointer slot for one file - no statistics, just the numbers."""
import struct, collections, sys
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
REC = 0x88
SLOTS = {0x28: "A", 0x50: "B", 0x58: "C", 0x60: "D"}

def run(name, path, show=24):
    b = L.load(path)
    n = len(b) // 8
    u = struct.unpack_from("<%dQ" % n, b, 0)
    per = collections.defaultdict(list)
    for i, q in enumerate(u):
        if 0 < q <= 0xFFFFFFFF and P_LO <= q <= P_HI:
            lab = SLOTS.get((i * 8) % REC)
            if lab:
                per[lab].append((i * 8, q - P_LO))
    print("### %s  size=%d  records~%d" % (name, len(b), len(b) // REC))
    for lab in "ABCD":
        L2 = per[lab]
        ds = [d for _, d in L2]
        print("\n-- slot %s (+0x%02X): %d pointers, %d distinct deltas" %
              (lab, [k for k, v in SLOTS.items() if v == lab][0], len(ds), len(set(ds))))
        if not ds:
            continue
        c = collections.Counter(ds)
        print("   top deltas: " + ", ".join("+%06X x%d" % (d, k) for d, k in c.most_common(8)))
        s = sorted(ds)
        print("   first 24 sorted: " + " ".join("%06X" % d for d in s[:show]))
        print("   last  12 sorted: " + " ".join("%06X" % d for d in s[-12:]))
        # gaps in the sorted unique list
        uq = sorted(set(ds))
        gp = collections.Counter(uq[i + 1] - uq[i] for i in range(len(uq) - 1))
        print("   common gaps: " + ", ".join("%d x%d" % (g, k) for g, k in gp.most_common(6)))

if __name__ == "__main__":
    A = dict(L.fam_a()); B = dict(L.fam_b())
    name = sys.argv[1]
    run(name, (A if name in A else B)[name])
