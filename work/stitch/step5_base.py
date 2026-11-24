"""step5_base.py - global pointer-target statistics across all 94 decoded chunks,
plus the window/base question: for every chunk, what is the best-fit base O and what does
the data at the target positions actually look like?
"""
import json, os, sys, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stitchlib as S

HERE = os.path.dirname(os.path.abspath(__file__))
meta = sorted(json.load(open(os.path.join(HERE, "streams_meta.json"))), key=lambda s: s["off"])


def plaintext(off):
    for fam, d in (("exact", r"work\codec\full\exact"), ("zd", r"work\codec\full\zeros_dict_unverified")):
        p = os.path.join(S.ROOT, d, "%s_%08X.bin" % (fam, off))
        if os.path.exists(p):
            return open(p, "rb").read()
    r = S.inflate(off)
    return r["out"] if r else b""


frags = []
for s in meta:
    b = plaintext(s["off"])
    ptrs = S.ptr_offsets(b)
    frags.append({"off": s["off"], "b": b, "ptr": ptrs,
                  "lo": s.get("lo"), "hi": s.get("hi")})

print("fragments with plaintext: %d" % len(frags))
print("total plaintext: %d, total pointers: %d" % (sum(len(f["b"]) for f in frags),
                                                   sum(len(f["ptr"]) for f in frags)))

# --- target value distribution ------------------------------------------------------
allt = [t for f in frags for (_, _, t) in f["ptr"]]
print("\n=== global pointer-target offset distribution (target = value & 0xFFFFFF) ===")
print("n=%d min 0x%X max 0x%X" % (len(allt), min(allt), max(allt)))
buckets = collections.Counter(t >> 16 for t in allt)
print("by 64K bucket (top 20):", sorted(buckets.items())[:20])
print("buckets used: %d of 256" % len(buckets))
print("frac >= 0x100000: %.3f" % (sum(1 for t in allt if t >= 0x100000) / len(allt)))

# --- per-fragment: best window base ------------------------------------------------
print("\n=== per-fragment best-fit base O (max #targets inside a buffer-sized window) ===")
print("  stream      size    nptr  tmin     tmax     bestO    inside  frac   O%4096  O%16")
rows = []
for f in frags:
    if len(f["ptr"]) < 4:
        continue
    ts = sorted(t for (_, _, t) in f["ptr"])
    N = len(f["b"])
    # sweep: O from tmin-N+1 .. tmin ; count in window
    best = (0, 0)
    for O in range(max(0, ts[0] - N + 1), ts[0] + 1):
        hi = O + N
        c = sum(1 for t in ts if O <= t < hi)
        if c > best[0]:
            best = (c, O)
    frac = best[0] / len(ts)
    rows.append((f["off"], N, len(ts), ts[0], ts[-1], best[1], best[0], frac))
for r in sorted(rows, key=lambda r: -r[7])[:25]:
    print("  0x%08X %6d %5d 0x%06X 0x%06X 0x%06X %5d %.3f  %4d   %2d" %
          (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[5] % 4096, r[5] % 16))
print("  ... %d fragments measured" % len(rows))
fr = [r[7] for r in rows]
print("  frac-inside: mean %.3f median %.3f min %.3f max %.3f" %
      (sum(fr) / len(fr), sorted(fr)[len(fr) // 2], min(fr), max(fr)))
json.dump([{"off": r[0], "size": r[1], "nptr": r[2], "tmin": r[3], "tmax": r[4],
            "bestO": r[5], "inside": r[6], "frac": r[7]} for r in rows],
          open(os.path.join(HERE, "base_probe.json"), "w"), indent=1)
