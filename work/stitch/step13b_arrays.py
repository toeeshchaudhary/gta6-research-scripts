"""step13b_arrays.py - same search, discriminative feature.

Feature: at an element address the 8 bytes are a HASH-LIKE word (> 2^40). Base rate in these
buffers is ~1/3 per 8-byte slot but only ~1/1000 for 4-byte-aligned arbitrary positions, so it
discriminates. Score = fraction of the target pattern whose positions hold a hash-like word.
"""
import json, os, sys, collections
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
# byte-level "next 4 bytes are large" mask at every byte offset (cheap proxy for hash-like)
MASK = {}
for o, b in CH.items():
    a = np.frombuffer(b, dtype=np.uint8)
    if len(a) < 12:
        continue
    big = (a.astype(np.uint16) << 8 | np.roll(a, -1).astype(np.uint16))
    MASK[o] = (big > 0x3F00).astype(np.float32)   # top byte >= 0x40 -> plausible hash high byte
print("corpus %d chunks" % len(CH))

GROUPS = []
for o in sorted(CH):
    by = collections.defaultdict(list)
    for k, so, t in S.ptr_offsets(CH[o]):
        by[so].append(t)
    for so, ts in by.items():
        if len(ts) >= 20:
            GROUPS.append((o, so, sorted(set(ts))))

print("groups >=20 targets: %d" % len(GROUPS))
print("  chunk      slot    n   best_chunk  p0       score   base = t0-p0 (mod 4096)")
out = []
for o, so, ts in GROUPS:
    t0 = ts[0]
    delta = np.array([t - t0 for t in ts])
    best = (0.0, None, None)
    for o2, m in MASK.items():
        n = len(m)
        span = int(delta[-1])
        if span + 8 >= n:
            continue
        L = n - span - 8
        sc = np.zeros(L, dtype=np.float32)
        for d in delta[::max(1, len(delta) // 40)]:
            sc += m[d:d + L]
        j = int(np.argmax(sc))
        k = len(delta[::max(1, len(delta) // 40)])
        v = float(sc[j]) / k
        if v > best[0]:
            best = (v, o2, j)
    base = (t0 - best[2]) if best[2] is not None else None
    out.append((o, so, len(ts), best[1], best[2], best[0], base))
    print("  0x%08X +0x%02X %4d  0x%08X 0x%06X  %.3f   %s" %
          (o, so, len(ts), best[1] or 0, best[2] or 0, best[0],
           ("0x%X (mod4096 %d)" % (base, base % 4096)) if base is not None else "-"))

sc = sorted(x[5] for x in out)
if sc:
    print("\nmedian score %.3f  max %.3f  n>=0.95: %d / %d" %
          (sc[len(sc) // 2], sc[-1], sum(1 for x in sc if x >= 0.95), len(sc)))
