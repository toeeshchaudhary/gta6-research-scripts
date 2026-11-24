import struct, os, glob, collections, math, json, sys

OUT = r"out"
WHDR = 20

def load_tables(prefix="all"):
    tabs = []
    for f in sorted(glob.glob(os.path.join(OUT, prefix + "_*.bin"))):
        if "_done" in f: continue
        d = open(f, "rb").read()
        p = 0
        while p + WHDR <= len(d):
            res, start, n = struct.unpack("<QII", d[p:p+16])
            kind = d[p+16]
            p += WHDR
            body = d[p:p+n*80]
            p += n*80
            if len(body) < n*80: break
            tabs.append((res, start, n, kind, body))
    return tabs

def merge(tabs):
    by = collections.defaultdict(list)
    for res, start, n, kind, body in tabs:
        by[(res, kind)].append((start, n, body))
    out = []
    for (res, kind), lst in by.items():
        lst.sort()
        cur = None
        for start, n, body in lst:
            if cur and cur[0] + cur[1]*80 == start:
                cur[2] += body; cur[1] += n
            else:
                if cur: out.append((res, cur[0], cur[1], kind, cur[2]))
                cur = [start, n, body]
        if cur: out.append((res, cur[0], cur[1], kind, cur[2]))
    return out

def wrec(body, i):
    r = body[i*80:(i+1)*80]
    pos = struct.unpack("<3f", r[0:12])
    yaw = struct.unpack("<f", r[12:16])[0]
    en = struct.unpack("<2I", r[0x10:0x18])
    ids = struct.unpack("<4I", r[0x20:0x30])
    return pos, yaw, en, ids

def mrec(body, i):
    r = body[i*80:(i+1)*80]
    pos = struct.unpack("<3f", r[0:12])
    h = struct.unpack("<I", r[0x0C:0x10])[0]
    sc = struct.unpack("<3f", r[0x10:0x1C])
    ptr = struct.unpack("<I", r[0x20:0x24])[0]
    tail = struct.unpack("<4I", r[0x34:0x44])
    return pos, h, sc, ptr, tail

def main():
    tabs = merge(load_tables())
    print("merged tables:", len(tabs))
    W = [(res, start, n, body) for res, start, n, kind, body in tabs if kind == 0]
    M = [(res, start, n, body) for res, start, n, kind, body in tabs if kind == 1]
    print("W tables %d (records %d, resources %d)" % (len(W), sum(t[2] for t in W), len({t[0] for t in W})))
    print("M tables %d (records %d, resources %d)" % (len(M), sum(t[2] for t in M), len({t[0] for t in M})))

    # ---- W statistics ----
    xs = []; ys = []; zs = []; yaws = []
    perres = {}
    for res, start, n, body in W:
        pts = []
        for i in range(n):
            pos, yaw, en, ids = wrec(body, i)
            xs.append(pos[0]); ys.append(pos[1]); zs.append(pos[2]); yaws.append(yaw)
            pts.append(pos)
        perres[res] = pts
    def q(v, p):
        v = sorted(v); return v[int(p*(len(v)-1))]
    print("W x  min %.1f max %.1f  q01 %.1f q50 %.1f q99 %.1f" % (min(xs), max(xs), q(xs,.01), q(xs,.5), q(xs,.99)))
    print("W y  min %.1f max %.1f  q01 %.1f q50 %.1f q99 %.1f" % (min(ys), max(ys), q(ys,.01), q(ys,.5), q(ys,.99)))
    print("W z  min %.1f max %.1f  q01 %.1f q50 %.1f q99 %.1f" % (min(zs), max(zs), q(zs,.01), q(zs,.5), q(zs,.99)))
    print("W zero-pos records:", sum(1 for x,y,z in zip(xs,ys,zs) if x==0 and y==0 and z==0))
    big = [a for a in yaws if abs(a) > math.pi*1.001]
    print("W |yaw| > pi: %d / %d" % (len(big), len(yaws)))

    # per-resource extent
    ext = []
    for res, pts in perres.items():
        if len(pts) < 2: continue
        mx = max(p[0] for p in pts); mn = min(p[0] for p in pts)
        my = max(p[1] for p in pts); ny = min(p[1] for p in pts)
        ext.append((max(mx-mn, my-ny), res, len(pts)))
    ext.sort()
    print("per-resource footprint (max of x/y extent): median %.1f  q90 %.1f  max %.1f" %
          (ext[len(ext)//2][0], ext[int(.9*len(ext))][0], ext[-1][0]))

    # spatial tiling: 500-unit cells
    cells = collections.Counter()
    for res, pts in perres.items():
        cx = int(sum(p[0] for p in pts)/len(pts)//500)
        cy = int(sum(p[1] for p in pts)/len(pts)//500)
        cells[(cx, cy)] += 1
    print("500-unit cells occupied: %d ; busiest cells: %s" % (len(cells), cells.most_common(5)))

    json.dump({"W_resources": len(perres), "W_records": len(xs),
               "cells_500": len(cells)},
              open(os.path.join(OUT, "stats_w.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
