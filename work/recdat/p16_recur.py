"""P16: how often does the big-endian page permutation recur inside a file?
If it recurs, the permutation is a per-sub-record header, not a whole-file container head.
Also: byte-value entropy profile per class (is there opcode density at all?).
"""
import struct, collections, math
import lib_recdat as L

PERMS = [[1, 6, 3, 0, 4, 5, 2], [2, 7, 4, 1, 5, 6, 0, 3], [2, 6, 3, 1, 4, 5, 0],
         [2, 8, 5, 0, 6, 7, 1, 4, 3], [3, 8, 5, 1, 6, 7, 0, 2, 4]]
out = []
w = out.append

def count_perm(b):
    """count occurrences of any known BE u16 permutation (2-byte aligned)"""
    hit = collections.Counter()
    for i in range(0, len(b) - 20, 2):
        for P in PERMS:
            n = len(P)
            if i + 2 * n > len(b):
                continue
            if all(struct.unpack_from(">H", b, i + 2 * k)[0] == P[k] for k in range(n)):
                hit[tuple(P)] += 1
                break
    return hit

def entropy(b):
    c = collections.Counter(b)
    n = float(len(b))
    h = -sum(v / n * math.log2(v / n) for v in c.values())
    return h, c[0] / n * 100.0, c[255] / n * 100.0, len(c)

for tag, files in (("A", L.fam_a()), ("B", L.fam_b())):
    w("=" * 96)
    w("FAMILY %s : permutation recurrence + byte profile" % tag)
    tot_hit = 0; tot_files = 0
    for name, p in files:
        b = L.load(p)
        h = count_perm(b)
        n = sum(h.values())
        if n:
            tot_hit += n; tot_files += 1
        e, z, ff, dist = entropy(b)
        w("%-42s %6d perms=%4d %-40s ent=%.2f zero=%4.1f%% ff=%4.1f%% distinct=%d" % (
            name[:42], len(b), n,
            " ".join("%s x%d" % (",".join(map(str, k)), v) for k, v in h.most_common(2)),
            e, z, ff, dist))
    w("")
    w("files containing at least one permutation: %d ; total occurrences: %d" % (tot_files, tot_hit))
open("p16.out", "w").write("\n".join(out))
print("\n".join(out))
