import struct, collections, math, json
import an2, an5

def main():
    T = an2.merge(an2.load_tables())
    decl = an5.load_decls()
    idx = collections.defaultdict(list)
    for res, start, n, kind, body in T:
        for i in range(n):
            r = body[i*80:(i+1)*80]
            if kind != 1: continue
            h = struct.unpack("<I", r[0x0C:0x10])[0]
            idx[h].append(res)
    parents = collections.Counter()
    for res in set(r for v in idx.values() for r in v):
        d = decl.get(res)
        if not d or d[1] is None: continue
        for p in idx[d[1]]:
            if p != res: parents[p] += 1
    top = parents.most_common(400)
    out = []
    print("top parent resources (MLO candidates):")
    for p, c in top[:15]:
        d = decl.get(p)
        print("  0x%-11X children=%-3d %s" % (p, c, d[0] if d else "-"))
    with open("out/targets.txt", "w") as f:
        # hashes of the parent resources themselves (so their placement record can be found)
        for p, c in top:
            d = decl.get(p)
            if d and d[1] is not None:
                f.write("%08X\n" % d[1])
                out.append(hex(p))
    print("target hashes written:", len(out))

if __name__ == "__main__":
    main()
