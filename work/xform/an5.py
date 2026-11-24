import struct, collections, math, json
import an2

def load_decls():
    d = {}
    for line in open(r"../../work/arch/dict/resnames_full.tsv", encoding="utf-8", errors="replace"):
        if line.startswith("#"): continue
        p = line.rstrip("\n").split("\t")
        if len(p) < 4: continue
        try: off = int(p[0], 16)
        except: continue
        if p[2].startswith("0x"):
            try: d[off] = (p[1], int(p[2], 16), p[3])
            except: d[off] = (p[1], None, p[3])
    return d

def quat_to_mat(q):
    x, y, z, w = q
    return ((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)),
            (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)),
            (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)))

def apply(m, v):
    return tuple(m[i][0]*v[0] + m[i][1]*v[1] + m[i][2]*v[2] for i in range(3))

def main():
    T = an2.merge(an2.load_tables())
    decl = load_decls()

    # index: archetype/child hash -> list of (kind, owner resource, pos, rot, scale)
    index = collections.defaultdict(list)
    for res, start, n, kind, body in T:
        for i in range(n):
            r = body[i*80:(i+1)*80]
            pos = struct.unpack("<3f", r[0:12])
            if kind == 0:
                for k in range(4):
                    h = struct.unpack("<I", r[0x20 + 4*k:0x24 + 4*k])[0]
                    yaw = struct.unpack("<f", r[12:16])[0]
                    index[h].append((0, res, pos, (0.0, 0.0, math.sin(yaw/2), math.cos(yaw/2)), (1, 1, 1)))
            else:
                h = struct.unpack("<I", r[0x0C:0x10])[0]
                sc = struct.unpack("<3f", r[0x10:0x1C])
                q = struct.unpack("<4f", r[0x40:0x50])
                nq = sum(v*v for v in q)
                if not (0.9 < nq < 1.1): q = (0.0, 0.0, 0.0, 1.0)
                if not all(0.01 < v < 100 for v in sc): sc = (1, 1, 1)
                index[h].append((1, res, pos, q, sc))
    print("indexed hash values:", len(index))

    Mres = collections.defaultdict(list)
    for res, start, n, kind, body in T:
        if kind != 0: continue
    for res, start, n, kind, body in T:
        if kind == 1: Mres[res].append(body)

    placed = {}
    noplace = 0
    for res, bodies in Mres.items():
        d = decl.get(res)
        if not d: noplace += 1; continue
        h = d[1]
        if h in index: placed[res] = (d, index[h])
        else: noplace += 1
    print("M resources with a world/parent placement:", len(placed), " without:", noplace)
    kinds = collections.Counter()
    for res, (d, lst) in placed.items():
        kinds[tuple(sorted({k for k, _, _, _, _ in lst}))] += 1
    print("parent record classes (0=world table, 1=interior table):", dict(kinds))

    # compose and measure coherence for resources whose parent is an interior record
    rows = []
    for res, (d, lst) in placed.items():
        name, h, tag = d
        bodies = Mres[res]
        pts = []
        for body in bodies:
            for i in range(len(body)//80):
                pts.append(struct.unpack("<3f", body[i*80:i*80+12]))
        for k, pres, ppos, pq, psc in lst[:4]:
            m = quat_to_mat(pq)
            world = []
            for p in pts:
                v = (p[0]*psc[0], p[1]*psc[1], p[2]*psc[2])
                rv = apply(m, v)
                world.append((ppos[0]+rv[0], ppos[1]+rv[1], ppos[2]+rv[2]))
            mx = [max(w[j] for w in world) for j in range(3)]
            mn = [min(w[j] for w in world) for j in range(3)]
            rows.append((res, name, tag, k, pres, len(pts),
                         math.dist(ppos, (ppos[0], ppos[1], ppos[2])), mn, mx))
    print("compositions computed:", len(rows))
    json.dump([[hex(r[0]), r[1], r[3], hex(r[4]), r[5], [round(v,2) for v in r[7]], [round(v,2) for v in r[8]]] for r in rows],
              open("out/mcompose.json", "w"), indent=0)

    # sanity: composition should keep the fragment near its parent
    ext = [(math.dist(r[7], r[8]), r[1], r[5], r[3]) for r in rows]
    ext.sort()
    print("\nsmallest composed diagonals (should be building-part sized, metres):")
    for e in ext[:6]: print("   %.2f m  %-45s n=%d parentkind=%d" % e)
    print("largest:")
    for e in ext[-6:]: print("   %.2f m  %-45s n=%d parentkind=%d" % e)

if __name__ == "__main__":
    main()
