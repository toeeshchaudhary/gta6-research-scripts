import struct, collections, math, json, statistics
import an2, an5

def main():
    T = an2.merge(an2.load_tables())
    decl = an5.load_decls()

    index = collections.defaultdict(list)
    for res, start, n, kind, body in T:
        for i in range(n):
            r = body[i*80:(i+1)*80]
            pos = struct.unpack("<3f", r[0:12])
            if kind == 1:
                h = struct.unpack("<I", r[0x0C:0x10])[0]
                q = struct.unpack("<4f", r[0x40:0x50])
                if not (0.9 < sum(v*v for v in q) < 1.1): q = (0.0, 0.0, 0.0, 1.0)
                index[h].append((res, pos, q))

    # child resource -> parent records
    childs = {}
    for res, start, n, kind, body in T:
        if kind != 1: continue
        d = decl.get(res)
        if not d or d[1] is None: continue
        if d[1] in index: childs[res] = (d, index[d[1]])
    byparent = collections.defaultdict(set)
    for res, (d, lst) in childs.items():
        for pres, ppos, pq in lst: byparent[pres].add(res)
    top = sorted(byparent.items(), key=lambda kv: -len(kv[1]))[:10]
    print("parents with most placed child resources:")
    for p, kids in top:
        pd = decl.get(p)
        print("  parent 0x%-10X children=%-3d  decl=%s" % (p, len(kids), pd[0] if pd else "-"))

    # choose the biggest parent that is a declared interior
    target = None
    for p, kids in top:
        pd = decl.get(p)
        if pd and (pd[0].startswith("int_") or pd[0].startswith("nm") or pd[0].startswith("v_int") or "#" in pd[2]):
            target = p; break
    if target is None: target = top[0][0]
    kids = sorted(byparent[target])
    print("\nchosen parent 0x%X with %d children (decl %s)" % (target, len(kids), decl.get(target, ("-",))[0]))

    # gather local points per child and compose
    def bodies_of(res):
        out = []
        for r2, s2, n2, k2, b2 in T:
            if r2 == res and k2 == 1: out.append(b2)
        return out

    allw = []
    per_child = {}
    for res in kids:
        d, lst = childs[res]
        pres, ppos, pq = lst[0]
        m = an5.quat_to_mat(pq)
        world = []
        for body in bodies_of(res):
            for i in range(len(body)//80):
                p = struct.unpack("<3f", body[i*80:i*80+12])
                rv = an5.apply(m, p)
                world.append((ppos[0]+rv[0], ppos[1]+rv[1], ppos[2]+rv[2]))
        per_child[res] = world
        allw += world

    print("composed instances:", len(allw), " over", len(kids), "child resources")
    if allw:
        mn = [min(w[j] for w in allw) for j in range(3)]
        mx = [max(w[j] for w in allw) for j in range(3)]
        print("composed footprint: x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f] diag=%.1f m" %
              (mn[0], mx[0], mn[1], mx[1], mn[2], mx[2], math.dist(mn, mx)))
        cen = [sum(w[j] for w in allw)/len(allw) for j in range(3)]
        print("composed centroid: (%.1f, %.1f, %.1f)" % tuple(cen))

    # sibling adjacency: nearest other-child centroid distance
    ctr = {}
    for res, w in per_child.items():
        if w: ctr[res] = (sum(p[0] for p in w)/len(w), sum(p[1] for p in w)/len(w), sum(p[2] for p in w)/len(w))
    nn = []
    keys = list(ctr)
    for i, a in enumerate(keys):
        ds = [math.dist(ctr[a], ctr[b]) for b in keys if b != a]
        if ds: nn.append(min(ds))
    if nn:
        print("sibling nearest-neighbour distance: median %.2f m, max %.2f m" % (statistics.median(nn), max(nn)))

    # before/after table for the child closest to the parent position
    pick = min(keys, key=lambda k: math.dist(ctr[k], (0, 0, 0)) if False else -len(per_child[k]))
    pick = max(per_child, key=lambda k: len(per_child[k]))
    print("\nbefore/after for child 0x%X (%s), parent 0x%X:" % (pick, decl[pick][0], target))
    print("  parent pos %s rot %s" % (childs[pick][1][0][1], childs[pick][1][0][2]))
    print("  %-32s %-34s %s" % ("local (as stored)", "world (transform applied)", "delta"))
    body = bodies_of(pick)[0]
    for i in range(min(12, len(body)//80)):
        p = struct.unpack("<3f", body[i*80:i*80+12])
        w = per_child[pick][i]
        print("  %-32s %-34s %.2f" % ("(%.3f, %.3f, %.3f)" % p,
                                     "(%.3f, %.3f, %.3f)" % w, math.dist(p, w)))
    json.dump({"parent": hex(target), "children": [hex(k) for k in kids],
               "composed_bbox": [mn, mx]}, open("out/mlo_proof.json", "w"), indent=1)

if __name__ == "__main__":
    main()
