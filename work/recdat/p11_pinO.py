"""P11: PIN THE FRAGMENT BASE.

Idea: if slot-A deltas name offsets inside the file, the same u32 values should also
appear as an ascending index table *inside* the file.  Find the file offset X where the
first delta's little-endian dword occurs as a data word (not as a pointer field).  Then
O = X - delta0 is the fragment base.  Verify: do several deltas all land on data words?
"""
import struct, collections, sys
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
REC = 0x88
SLOTS = {0x28: "A", 0x50: "B", 0x58: "C", 0x60: "D"}

def analyze(name, path):
    b = L.load(path)
    n = len(b) // 8
    u = struct.unpack_from("<%dQ" % n, b, 0)
    per = collections.defaultdict(list)
    for i, q in enumerate(u):
        if 0 < q <= 0xFFFFFFFF and P_LO <= q <= P_HI:
            lab = SLOTS.get((i * 8) % REC)
            if lab:
                per[lab].append((i * 8, q - P_LO))
    print("### %s size=%d" % (name, len(b)))
    # byte-offset of every dword value -> list of file offsets
    idx = collections.defaultdict(list)
    for i in range(len(b) // 4):
        v = struct.unpack_from("<I", b, i * 4)[0]
        idx[v].append(i * 4)
    for lab in "ACD":
        ds = sorted(set(d for _, d in per[lab]))
        if not ds:
            continue
        # candidate O from matching the most deltas at a consistent shift
        best = collections.Counter()
        for d in ds:
            for off in idx.get(d, []):
                best[off - d] += 1
        if not best:
            print("  slot %s: no delta value occurs as a data word" % lab); continue
        O, k = best.most_common(1)[0]
        print("  slot %s: %d targets; best O=0x%X matches %d/%d deltas as data words" % (lab, len(ds), O, k, len(ds)))
        # how many of the deltas that DO appear, appear at file offset delta-O ?
        good = sum(1 for d in ds if (d - O) in idx.get(d, []))
        print("         of which at exactly delta-O: %d/%d" % (good, len(ds)))

if __name__ == "__main__":
    A = dict(L.fam_a()); B = dict(L.fam_b())
    for name in sys.argv[1:]:
        analyze(name, (A if name in A else B)[name])
