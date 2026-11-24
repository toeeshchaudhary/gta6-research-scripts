import struct, os, glob, collections, math, json, pickle
import an2

TABS = None
def tabs():
    global TABS
    if TABS is None:
        TABS = an2.merge(an2.load_tables())
    return TABS

def load_decls():
    d = {}
    for line in open(r"..\\..\\work\\arch\dict\resnames_full.tsv", encoding="utf-8", errors="replace"):
        if line.startswith("#"): continue
        p = line.rstrip("\n").split("\t")
        if len(p) < 4: continue
        try: off = int(p[0], 16)
        except: continue
        d[off] = (p[1], int(p[2], 16) if p[2].startswith("0x") else None, p[3])
    return d

def load_names():
    n = {}
    for line in open(r"..\\..\\work\\arch\dict\d3_names.tsv", encoding="utf-8", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 2: continue
        try: h = int(p[0], 16)
        except: continue
        n[h] = p[1]
    return n

def main():
    T = tabs()
    W = {}
    for res, start, n, kind, body in T:
        if kind != 0: continue
        lst = W.setdefault(res, [])
        for i in range(n):
            pos, yaw, en, ids = an2.wrec(body, i)
            lst.append((pos, yaw, en, ids))
    decl = load_decls()
    print("W resources:", len(W))

    # classify per resource
    loc = []   # resources whose records are all within 400 of the origin
    spread = []
    for res, lst in W.items():
        mx = max(max(abs(p[0][0]), abs(p[0][1])) for p in lst)
        (loc if mx < 400 else spread).append((res, lst, mx))
    print("origin-local resources (<400 units):", len(loc), " records", sum(len(l) for _,l,_ in loc))
    print("map-spread resources:", len(spread), " records", sum(len(l) for _,l,_ in spread))

    loc.sort(key=lambda t: -len(t[1]))
    print("\nbiggest origin-local resources:")
    for res, lst, mx in loc[:12]:
        d = decl.get(res)
        pts = [p[0] for p in lst]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
        print("  0x%X n=%-5d extent=%6.1f  x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f] decl=%s" %
              (res, len(lst), mx, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs),
               (d[0] if d else "-")))

    # distinct positions in the densest 200-unit cell at origin
    cell = [p for res, lst, mx in loc for p in lst if abs(p[0][0]) < 100 and abs(p[0][1]) < 100]
    print("\nrecords within 100 units of origin: %d ; distinct positions %d" %
          (len(cell), len({(round(p[0][0],3), round(p[0][1],3), round(p[0][2],3)) for p in cell})))
    allrec = [p for res, lst, mx in loc for p in lst]
    print("all origin-local records: %d ; distinct positions %d" %
          (len(allrec), len({(round(p[0][0],3), round(p[0][1],3), round(p[0][2],3)) for p in allrec})))
    zero = sum(1 for p in allrec if p[0] == (0.0, 0.0, 0.0))
    print("origin-local records at exactly (0,0,0):", zero)

    pickle.dump({"n_loc": len(loc), "n_spread": len(spread)}, open("out/pop.pkl","wb"))

if __name__ == "__main__":
    main()
