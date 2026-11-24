"""P6: test the 'header + N records of fixed stride' hypothesis on the H-class files.

H-class head = u64 0, u64 N (count), u64 hash64, u64 flag/hash, u64 flag, u64 ptr...
Hypothesis: records start at some phase P with stride S, and N (the u64 at +0x08)
equals the record count.  Score (P,S) by how many record slots hold a 0x50xxxxxx
pointer in dword 0 / how regular the slot classes are.
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
out = []
w = out.append

def cls(v):
    if v == 0: return "0"
    if v == 0xFFFFFFFF: return "S"
    if P_LO <= v <= P_HI: return "P"
    if 0 < v < 0x100: return "s"
    return "."

for name, p in L.fam_a() + L.fam_b():
    b = L.load(p)
    d = L.u32s(b)
    if not (d[0] == 0 and d[1] == 0 and d[3] == 0):
        continue                      # not H-class head
    N = d[2] | (d[3] << 32)
    # score strides: for each S, count slots (from phase P) where dword0 is a pointer
    best = []
    for S in range(8, 0x200, 8):
        for phase in range(0, min(S, 0x110), 8):
            if phase == 0:
                continue
            n = (len(d) * 4 - phase) // S
            if n < 4:
                continue
            ptr0 = sum(1 for k in range(n) if P_LO <= d[(phase + k * S) // 4] <= P_HI)
            if ptr0 >= 3:
                best.append((ptr0 / float(n), S, phase, n, ptr0))
    best.sort(reverse=True)
    w("%-42s size=%6d  N(+0x08)=%-6d dwords=%d" % (name, len(b), N, len(d)))
    for sc, S, phase, n, ptr0 in best[:3]:
        w("      stride 0x%-3X phase 0x%-3X  slots=%4d ptr0=%4d  (%.0f%% ptr in slot 0)  N*S+phase=%d"
          % (S, phase, n, ptr0, 100 * sc, N * S + phase))
    # does N*S+phase == filesize?
    for sc, S, phase, n, ptr0 in best[:1]:
        w("      N*S+phase=%d  filesize=%d  ratio=%.3f" % (N * S + phase, len(b), (N * S + phase) / float(len(b))))
open("p6.out", "w").write("\n".join(out))
print("\n".join(out))
