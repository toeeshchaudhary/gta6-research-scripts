import struct, collections, math, json, statistics
import an2

def main():
    T = an2.merge(an2.load_tables())
    recs = []
    for res, start, n, kind, body in T:
        if kind != 0: continue
        for i in range(n):
            r = body[i*80:(i+1)*80]
            p = struct.unpack("<3f", r[0:12])
            yaw = struct.unpack("<f", r[12:16])[0]
            ids = struct.unpack("<4I", r[0x20:0x30])
            recs.append({"pos": [p[0], p[1], p[2]], "rot": [0.0, 0.0, math.sin(yaw/2), math.cos(yaw/2)],
                         "hash": "0x%08X" % ids[3], "resource": "0x%X" % res})
    print("records", len(recs))
    json.dump({"source": "GTA VI levels.rpf.part class-S placement tables (work/xform)",
               "format": "pos@+0x00 f3 (world), yaw@+0x0C, archetype hash @+0x2C",
               "counts": {"instances": len(recs),
                          "resources": len({r["resource"] for r in recs}),
                          "distinct_archetype_hashes": len({r["hash"] for r in recs})},
               "instances": recs}, open("out/scene_S.json", "w"))

    # 1-metre occupancy: do two different resources claim the same cubic metre?
    cell = collections.defaultdict(set)
    for r in recs:
        p = r["pos"]
        cell[(round(p[0]), round(p[1]), round(p[2]))].add(r["resource"])
    shared = sum(1 for v in cell.values() if len(v) > 1)
    print("1 m cells occupied: %d ; shared by >1 resource: %d (%.2f%%)" % (len(cell), shared, 100.0*shared/len(cell)))
    multi = collections.Counter(len(v) for v in cell.values())
    print("  resources per 1 m cell:", dict(sorted(multi.items())))

    # street-run coherence: within one resource, consecutive records should be a smooth chain
    seg = []
    for res, start, n, kind, body in T:
        if kind != 0 or n < 20: continue
        prev = None; ds = []
        for i in range(n):
            p = struct.unpack("<3f", body[i*80:i*80+12])
            if prev: ds.append(math.dist(prev, p))
            prev = p
        if ds: seg.append((statistics.median(ds), res, n))
    seg.sort()
    print("\nmedian step between consecutive records (same resource):")
    print("  overall median %.2f m over %d resources with n>=20" % (statistics.median([s[0] for s in seg]), len(seg)))
    for s in seg[:5]: print("   %.2f m  0x%X n=%d" % s)
    for s in seg[-5:]: print("   %.2f m  0x%X n=%d" % s)

    zs = sorted(r["pos"][2] for r in recs)
    print("\nz percentiles: q01 %.1f q10 %.1f q50 %.1f q90 %.1f q99 %.1f" %
          tuple(zs[int(p*(len(zs)-1))] for p in (.01,.1,.5,.9,.99)))

if __name__ == "__main__":
    main()
