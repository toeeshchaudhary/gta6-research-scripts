"""step13_arrays.py - find the arrays that the pointers name, anywhere in the corpus.

If a chunk's slot-k target list is an ascending list of element addresses t0<t1<...<tn, then the
array itself is a zone in SOME chunk where the element positions are p0 + (tk - t0). Test every
chunk and every start p0: score = fraction of the pattern positions that hold a plausible array
word (small u32 / 0 / 0xFFFFFFFF / RAGE pointer). A true array scores ~1.0.
"""
import json, os, sys, struct, collections
import numpy as np
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


CH = {s["off"]: plaintext(s["off"]) for s in meta}
print("corpus: %d chunks, %d B" % (len(CH), sum(len(b) for b in CH.values())))

BOO = {}
for o, b in CH.items():
    n = (len(b) - 4) // 4
    if n <= 0:
        continue
    a = np.frombuffer(b[:n * 4], dtype="<u4")
    ok = ((a > 0) & (a < 0x100000)) | (a == 0) | (a == 0xFFFFFFFF) | \
         ((a >= 0x50000000) & (a <= 0x50FFFFFF))
    # smooth: a word counts if it or its neighbour is plausible (elements are 2+ words)
    BOO[o] = ok.astype(np.float32)

GROUPS = []
for o in sorted(CH):
    b = CH[o]
    by = collections.defaultdict(list)
    for k, so, t in S.ptr_offsets(b):
        by[so].append(t)
    for so, ts in by.items():
        if len(ts) >= 12:
            GROUPS.append((o, so, sorted(set(ts))))

print("slot groups with >=12 targets: %d" % len(GROUPS))

print("\n=== searching the corpus for each group's array ===")
print("  chunk      slot    n   best_chunk  p0      score   delta_align")
results = []
for o, so, ts in GROUPS:
    if len(ts) < 12:
        continue
    delta = np.array([t - ts[0] for t in ts])
    # step 2 elements to keep it fast but robust
    sub = delta[::2] if len(delta) > 60 else delta
    step4 = (sub % 4 == 0).all()
    best = (0.0, None, None)
    for o2, ok in BOO.items():
        n = len(ok)
        span = int(sub[-1]) // 4
        if span + 2 >= n:
            continue
        if not step4:
            # unaligned pattern: build shifted bool
            b2 = CH[o2]
            m = (len(b2) - 4) // 4
            a = np.frombuffer(b2[:m * 4], dtype="<u4")
            okk = (((a > 0) & (a < 0x100000)) | (a == 0) | (a == 0xFFFFFFFF)).astype(np.float32)
            idx = sub
            L = n - span - 2
            sc = np.zeros(L, dtype=np.float32)
            for d in idx:
                sc += okk[d // 4: d // 4 + L]
            j = int(np.argmax(sc))
            sc = sc[j] / len(sub)
            p0 = j * 4
        else:
            L = n - span - 2
            sc = np.zeros(L, dtype=np.float32)
            for d in sub:
                sc += ok[d // 4: d // 4 + L]
            j = int(np.argmax(sc))
            sc = sc[j] / len(sub)
            p0 = j * 4
        if sc > best[0]:
            best = (float(sc), o2, p0)
    results.append((o, so, len(ts), best[1], best[2], best[0], step4))
    print("  0x%08X +0x%02X %4d  0x%08X 0x%06X  %.3f   %s" %
          (o, so, len(ts), best[1], best[2] or 0, best[0], step4))

json.dump([{"chunk": "0x%08X" % r[0], "slot": r[1], "ntargets": r[2],
            "best_chunk": ("0x%08X" % r[3]) if r[3] else None, "p0": r[4],
            "score": round(r[5], 4), "aligned": bool(r[6])} for r in results],
          open(os.path.join(HERE, "arraysearch.json"), "w"), indent=1)
sc = sorted(r[5] for r in results)
print("\nscore distribution: median %.3f  max %.3f  n>=0.90: %d" %
      (sc[len(sc) // 2], sc[-1], sum(1 for x in sc if x >= 0.9)))
