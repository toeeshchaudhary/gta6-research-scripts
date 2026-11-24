"""P14: hierarchy evidence.
(a) strict page-permutation test: [u16 N][N u16 = permutation of 0..N-1] at phase 0,
    or a bare permutation of 0..M-1 at phase 0/1.
(b) record -> record edges: a pointer whose delta is a nonzero multiple of 0x88 names
    record k of the array if the array base is absolute 0.  How many such edges exist?
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
REC = 0x88
SLOTS = {0x28: "A", 0x50: "B", 0x58: "C", 0x60: "D"}
out = []
w = out.append

def perm_forms(b):
    res = []
    for ph in (0, 1, 2):
        v = [struct.unpack_from("<H", b, ph + 2 * k)[0] for k in range(16) if ph + 2 * k + 2 <= len(b)]
        for n in range(3, 14):
            if n < len(v) and v[0] == n and sorted(v[1:n + 1]) == list(range(n)):
                res.append(("counted", ph, n, v[1:n + 1]))
                break
        for n in range(3, 14):
            if sorted(v[:n]) == list(range(n)):
                res.append(("bare", ph, n, v[:n]))
                break
    return res

for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    w("=" * 96)
    w("FAMILY %s" % tag)
    w("%-42s %-34s %s" % ("file", "page permutation", "record->record edges"))
    tot_edges = 0
    for name, p in files:
        b = L.load(p)
        pf = perm_forms(b)
        n = len(b) // 8
        u = struct.unpack_from("<%dQ" % n, b, 0)
        edges = []
        for i, q in enumerate(u):
            if 0 < q <= 0xFFFFFFFF and P_LO <= q <= P_HI:
                d = q - P_LO
                if d and d % REC == 0:
                    k = d // REC
                    if k * REC < len(b):
                        edges.append((i * 8, SLOTS.get((i * 8) % REC), k))
        tot_edges += len(edges)
        pfs = "; ".join("%s phase%d n=%d %s" % (a, c, d, "[" + ",".join(map(str, e)) + "]") for a, c, d, e in pf) or "-"
        w("%-42s %-34s %d in-array edges%s" % (
            name[:42], pfs[:34], len(edges),
            (": " + str([(hex(o), s, k) for o, s, k in edges[:4]])) if edges else ""))
    w("total record->record edges: %d" % tot_edges)
open("p14.out", "w").write("\n".join(out))
print("\n".join(out))
