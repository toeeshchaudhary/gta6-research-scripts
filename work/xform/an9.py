import struct, collections, math, statistics, json
import an2

def main():
    T = an2.merge(an2.load_tables())
    W = [(res, n, body) for res, start, n, kind, body in T if kind == 0]
    M = [(res, n, body) for res, start, n, kind, body in T if kind == 1]
    nw = sum(t[1] for t in W)
    print("placement (class S) tables %d records %d resources %d" % (len(W), nw, len({t[0] for t in W})))
    print("definition (class M) tables %d records %d resources %d" % (len(M), sum(t[1] for t in M), len({t[0] for t in M})))

    xs = []; ys = []; zs = []
    per = {}
    for res, n, body in W:
        pts = []
        for i in range(n):
            r = body[i*80:(i+1)*80]
            p = struct.unpack("<3f", r[0:12])
            pts.append(p)
            xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
        per.setdefault(res, []).extend(pts)
    def q(v, a):
        v = sorted(v); return v[int(a*(len(v)-1))]
    print("S x[%.1f,%.1f] q01 %.1f q50 %.1f q99 %.1f" % (min(xs), max(xs), q(xs,.01), q(xs,.5), q(xs,.99)))
    print("S y[%.1f,%.1f] q01 %.1f q50 %.1f q99 %.1f" % (min(ys), max(ys), q(ys,.01), q(ys,.5), q(ys,.99)))
    print("S z[%.1f,%.1f] q01 %.1f q50 %.1f q99 %.1f" % (min(zs), max(zs), q(zs,.01), q(zs,.5), q(zs,.99)))
    print("distinct positions %d / %d" % (len({(round(a,2),round(b,2),round(c,2)) for a,b,c in zip(xs,ys,zs)}), len(xs)))
    print("records at (0,0,0):", sum(1 for a,b,c in zip(xs,ys,zs) if a==0 and b==0 and c==0))

    # per-resource tiling: bounding box of each resource, then overlap rate between neighbours
    boxes = {}
    for res, pts in per.items():
        if len(pts) < 2: continue
        boxes[res] = (min(p[0] for p in pts), min(p[1] for p in pts),
                      max(p[0] for p in pts), max(p[1] for p in pts))
    print("resources with a 2D bbox:", len(boxes))
    areas = [(b[2]-b[0])*(b[3]-b[1]) for b in boxes.values()]
    print("footprint area: median %.0f m^2, sum %.0f m^2" % (statistics.median(areas), sum(areas)))

    # cells at 100 units: overlap = how many resources claim the same 100-unit cell
    cells = collections.defaultdict(int)
    for res, b in boxes.items():
        for cx in range(int(b[0]//100), int(b[2]//100)+1):
            for cy in range(int(b[1]//100), int(b[3]//100)+1):
                cells[(cx,cy)] += 1
    if cells:
        occ = collections.Counter(cells.values())
        tot = len(cells)
        multi = sum(v for k, v in occ.items() if k > 1)
        print("100-unit cells with >=1 resource bbox: %d ; cells claimed by >1 resource: %.1f%%" % (tot, 100.0*multi/tot))
        print("  distribution of resources-per-cell:", dict(sorted(occ.items())[:8]))

    # nearest neighbour distance between resource centroids
    ctr = [( (b[0]+b[2])/2, (b[1]+b[3])/2 ) for b in boxes.values()]
    ctr.sort()
    nn = []
    for i in range(min(len(ctr), 4000)):
        best = 1e9
        for j in range(max(0,i-6), min(len(ctr), i+6)):
            if i == j: continue
            best = min(best, math.dist(ctr[i], ctr[j]))
        if best < 1e8: nn.append(best)
    if nn:
        print("resource centroid nearest-neighbour distance: median %.1f m, q10 %.1f, q90 %.1f" %
              (statistics.median(nn), q(nn,.1), q(nn,.9)))
    json.dump({"S_records": nw, "S_resources": len(per), "S_bbox_resources": len(boxes),
               "median_footprint_m2": statistics.median(areas)}, open("out/final_S.json","w"), indent=1)

if __name__ == "__main__":
    main()
