"""P15: hunt for jump/switch tables: ascending u32 runs preceded by their own count,
with small deltas (rewrite lengths) - the shape a serialised switch table has.
"""
import struct, collections
import lib_recdat as L

P_LO, P_HI = 0x50000000, 0x50FFFFFF
out = []
w = out.append

def runs(b, minlen=6, maxval=0x1000000):
    d = [struct.unpack_from("<I", b, i * 4)[0] for i in range(len(b) // 4)]
    res, i = [], 0
    while i < len(d) - minlen:
        j = i
        while j + 1 < len(d) and d[j + 1] > d[j] and d[j + 1] < maxval:
            j += 1
        if j - i + 1 >= minlen:
            res.append((i, j))
            i = j + 1
        else:
            i += 1
    return d, res

hits = []
for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    for name, p in files:
        b = L.load(p)
        d, rr = runs(b)
        for i, j in rr:
            v = d[i:j + 1]
            gaps = [v[k + 1] - v[k] for k in range(len(v) - 1)]
            cnt = d[i - 1] if i >= 1 else None
            span = v[-1] - v[0]
            # "rewrite lengths": all gaps <= 64
            small = all(2 <= g <= 64 for g in gaps)
            hits.append((small, cnt == len(v), len(v), name, i * 4, span, max(gaps), min(gaps), v[:8]))

hits.sort(key=lambda h: (-h[1], -h[0], -h[2]))
w("ascending u32 runs, best first (count==len means the dword before the run equals its")
w("length - the signature of a serialised switch/jump table):")
w("  %-42s off      n  cntOK gapsMax gapsMin span" % "file")
for small, cntok, n, name, off, span, gmax, gmin, head in hits[:26]:
    w("  %-42s %06X %3d  %-5s %6d %6d %8X  %s" % (
        name[:42], off, n, "YES" if cntok else "no", gmax, gmin, span,
        " ".join(str(x) for x in head[:6])))
open("p15.out", "w").write("\n".join(out))
print("\n".join(out))
