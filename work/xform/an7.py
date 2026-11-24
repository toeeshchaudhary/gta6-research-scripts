import struct, collections, math, json, statistics
import an2, an5

MAXD = 7

def main():
    T = an2.merge(an2.load_tables())
    decl = an5.load_decls()

    # hash -> [(kind, owner_resource, pos, quat)]
    index = collections.defaultdict(list)
    mres = {}
    wres = set()
    for res, start, n, kind, body in T:
        if kind == 0: wres.add(res)
        for i in range(n):
            r = body[i*80:(i+1)*80]
            pos = struct.unpack("<3f", r[0:12])
            if kind == 1:
                h = struct.unpack("<I", r[0x0C:0x10])[0]
                q = struct.unpack("<4f", r[0x40:0x50])
                if not (0.9 < sum(v*v for v in q) < 1.1): q = (0.0, 0.0, 0.0, 1.0)
                sc = struct.unpack("<3f", r[0x10:0x1C])
                if not all(0.01 < v < 100 for v in sc): sc = (1.0, 1.0, 1.0)
                index[h].append((1, res, pos, q, sc))
                mres.setdefault(res, []).append((pos, h, q, sc))
            else:
                for k in range(4):
                    h = struct.unpack("<I", r[0x20 + 4*k:0x24 + 4*k])[0]
                    yaw = struct.unpack("<f", r[12:16])[0]
                    index[h].append((0, res, pos, (0.0, 0.0, math.sin(yaw/2), math.cos(yaw/2)), (1.0, 1.0, 1.0)))

    # per-resource placement (owner must differ from self)
    place = {}
    for res in mres:
        d = decl.get(res)
        if not d or d[1] is None: continue
        for rec in index.get(d[1], ()):
            if rec[1] != res:
                place[res] = rec
                break

    chains = {}
    def resolve(res, depth, seen):
        """return list of (world_pos, quat, scale) for this resource, or None"""
        if res in seen or depth > MAXD: return None
        rec = place.get(res)
        if rec is None: return None
        kind, owner, pos, q, sc = rec
        if kind == 0:
            return [(pos, q, sc)]
        up = resolve(owner, depth+1, seen | {res})
        if up is None: return None
        out = []
        mq = an5.quat_to_mat(q)
        for (wp, wq, wsc) in up:
            rq = an5.apply(an5.quat_to_mat(wq), pos)
            wp2 = (wp[0]+rq[0], wp[1]+rq[1], wp[2]+rq[2])
            out.append((wp2, (wq[0]+q[0], wq[1]+q[1], wq[2]+q[2], wq[3]+q[3]), sc))
        return out

    for res in mres: chains[res] = resolve(res, 0, frozenset())

    ok = {r: c for r, c in chains.items() if c}
    print("M resources:", len(mres), " resolved to a world record:", len(ok))
    depths = collections.Counter()
    for res, c in ok.items():
        d = 0; cur = res
        while True:
            rec = place.get(cur)
            if rec is None: break
            d += 1
            if rec[0] == 0: break
            cur = rec[1]
        depths[d] += 1
    print("chain depth distribution:", dict(sorted(depths.items())))

    # compose local points to world
    def world_points(res):
        out = []
        for (wp, wq, wsc) in chains[res]:
            m = an5.quat_to_mat(wq)
            for (p, h, q, sc) in mres[res]:
                v = (p[0]*sc[0], p[1]*sc[1], p[2]*sc[2])
                rv = an5.apply(m, v)
                out.append((wp[0]+rv[0], wp[1]+rv[1], wp[2]+rv[2]))
        return out

    allpts = []
    per = {}
    for res in ok:
        w = world_points(res)
        per[res] = w
        allpts += w
    if allpts:
        xs = [p[0] for p in allpts]; ys = [p[1] for p in allpts]; zs = [p[2] for p in allpts]
        print("composed instances:", len(allpts))
        print("composed x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f]" % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
        print("median |xy| of composed points: %.1f (before, local: %.1f)" %
              (statistics.median([math.hypot(x, y) for x, y in zip(xs, ys)]),
               statistics.median([math.hypot(*struct.unpack("<3f", b[i*80:i*80+12])[:2])
                                  for r2, s2, n2, k2, b in T if k2 == 1 for i in range(n2)])))

    # group by top-level world parent and measure sibling adjacency vs stranger distance
    ctr = {}
    for res, w in per.items():
        if w: ctr[res] = (sum(p[0] for p in w)/len(w), sum(p[1] for p in w)/len(w), sum(p[2] for p in w)/len(w))

    rows = []
    for res, w in per.items():
        if not w: continue
        mn = [min(p[j] for p in w) for j in range(3)]
        mx = [max(p[j] for p in w) for j in range(3)]
        rows.append((res, decl[res][0], len(w), math.dist(mn, mx), ctr[res]))
    rows.sort(key=lambda r: -r[2])
    print("\nlargest resolved fragment clouds:")
    for r in rows[:10]:
        print("  0x%-11X %-45s n=%-4d diag=%6.2f m centroid=(%.0f,%.0f,%.0f)" % (r[0], r[1], r[2], r[3], *r[4]))

    # before/after table for the biggest cloud
    if rows:
        tgt = rows[0][0]
        print("\nBEFORE/AFTER for 0x%X (%s):" % (tgt, decl[tgt][0]))
        w = per[tgt]
        for i in range(min(10, len(w))):
            p = mres[tgt][i][0]
            print("   local (%9.3f,%9.3f,%9.3f)  ->  world (%10.3f,%10.3f,%10.3f)" % (*p, *w[i]))
    json.dump({hex(r[0]): {"name": r[1], "n": r[2], "diag": round(r[3], 2), "centroid": [round(v, 1) for v in r[4]]} for r in rows},
              open("out/resolved.json", "w"), indent=0)

if __name__ == "__main__":
    main()
