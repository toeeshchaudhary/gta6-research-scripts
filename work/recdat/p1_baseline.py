"""P1: baseline measurements on the two families.
M1 pointer dword-index parity & alignment
M2 per-file delta span vs file size (is a file a page of a bigger resource?)
M3 sorted delta gap structure
M4 which byte lanes hold the 0x50 high byte
"""
import sys, struct, collections
import lib_recdat as L

def scan(files, tag):
    print("=" * 70)
    print("FAMILY", tag, len(files), "files")
    # M1
    idx = collections.Counter()      # dword index within 8-byte record
    lane = collections.Counter()     # byte lane of the 0x50 high byte
    nptr = 0; nw = 0
    per_file = {}
    all_deltas = collections.Counter()
    for name, p in files:
        b = L.load(p)
        w = L.u32s(b)
        nw += len(w)
        ds = []
        for i, v in enumerate(w):
            if L.is_ptr(v):
                nptr += 1
                idx[i % 2] += 1
                # find which byte lane carries the 0x50
                lane_i = None
                for k in range(4):
                    if ((v >> (8 * k)) & 0xFF) == 0x50:
                        lane_i = k
                lane[(i * 4) + (lane_i if lane_i is not None else -1)] += 1
                ds.append(v - L.PTR_BASE)
                all_deltas[v - L.PTR_BASE] += 1
        per_file[name] = (len(b), ds)
    print("dwords=%d  pointers=%d (%.1f per 1000 dwords)" % (nw, nptr, 1000.0 * nptr / nw))
    print("M1 dword index parity: even=%d odd=%d  -> %.1f%% even" %
          (idx[0], idx[1], 100.0 * idx[0] / max(1, nptr)))
    print("M1 byte lane of 0x50 within the record (byte idx mod 8):",
          {k: v for k, v in sorted(lane.items())})
    # M2
    print("M2 per-file delta span vs size")
    print("  %-28s %7s %5s %9s %9s %9s %6s" % ("file", "size", "nptr", "min", "max", "span", "span/size"))
    ok8 = 0; tot8 = 0
    for name, (sz, ds) in sorted(per_file.items()):
        if not ds:
            print("  %-28s %7d %5d  (no pointers)" % (name, sz, 0)); continue
        mn, mx = min(ds), max(ds)
        span = mx - mn
        print("  %-28s %7d %5d %9X %9X %9X %6.2f" % (name, sz, len(ds), mn, mx, span, span / float(sz)))
        for d in ds:
            tot8 += 1
            if d % 8 == 0:
                ok8 += 1
    print("M2 deltas %%8==0: %d/%d = %.1f%%" % (ok8, tot8, 100.0 * ok8 / tot8))
    # M3 global delta census
    print("M3 distinct deltas=%d  repeat rate=%.2f  top:" % (len(all_deltas), nptr / float(len(all_deltas))))
    for d, c in all_deltas.most_common(12):
        print("   +%06X  x%d" % (d, c))
    return per_file


A = L.fam_a(); B = L.fam_b()
scan(A, "A")
scan(B, "B")
