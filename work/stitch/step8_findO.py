"""step8_findO.py - recover the fragment base O from STRUCTURE, not from counting.

For each pointer-rich chunk and every candidate base O in the admissible interval, score the
bytes found at the pointer targets: a real pointer target should sit on an array element, i.e.
a run of small u32 values (RECDAT's index tables), not on noise. Report the peak and whether it
is unique. Also report the same score for a random-offset control.
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


def elem_score(b, p, n=4):
    """how much do the n u32s at b[p:] look like a table entry?  0..1"""
    if p < 0 or p + 4 * n > len(b):
        return 0.0
    v = struct.unpack_from("<%dI" % n, b, p)
    ok = 0
    for x in v:
        if 0 < x < 0x100000:
            ok += 1
        elif x == 0 or x == 0xFFFFFFFF:
            ok += 0.3
        elif 0x50000000 <= x <= 0x50FFFFFF:
            ok += 0.5
    return ok / n


def sweep(fr, step=1):
    b = fr["b"]
    ts = sorted(t for (_, _, t) in fr["ptr"])
    N = len(b)
    best = (0.0, None)
    curve = []
    lo = max(0, ts[0] + 4 - N)
    for O in range(lo, ts[0] + 1, step):
        s = sum(elem_score(b, t - O) for t in ts[:60])
        curve.append((O, s))
        if s > best[0]:
            best = (s, O)
    return best, curve


frags = []
for s in meta:
    b = plaintext(s["off"])
    ptrs = S.ptr_offsets(b)
    if len(ptrs) >= 8:
        frags.append({"off": s["off"], "b": b, "ptr": ptrs})

print("pointer-rich chunks: %d" % len(frags))
print("  chunk       N     nptr  bestO    score  nxt_best  gap   O%%4096  O%%16  score@O=0  rand_mean")
res = []
for fr in frags:
    b = fr["b"]
    ts = sorted(t for (_, _, t) in fr["ptr"])
    (sc, O), curve = sweep(fr)
    vals = sorted(curve, key=lambda kv: -kv[1])
    second = 0.0
    for O2, s2 in vals:
        if abs(O2 - O) > 64:
            second = s2
            break
    zero = sum(elem_score(b, t) for t in ts[:60]) if ts[0] + 4 * 4 < len(b) else 0.0
    # random control: same n positions at random offsets
    import random
    random.seed(7)
    ctrl = []
    for _ in range(20):
        p0 = random.randrange(0, max(1, len(b) - 64))
        ctrl.append(sum(elem_score(b, min(len(b) - 64, p0 + 4 * i)) for i in range(min(60, len(ts)))))
    cm = sum(ctrl) / len(ctrl)
    res.append({"off": fr["off"], "N": len(b), "nptr": len(ts), "O": O, "score": sc,
                "second": second, "zero": zero, "ctrl": cm})
    print("  0x%08X %6d %5d 0x%06X %6.1f  %6.1f  %5.1f  %4d  %3d  %6.1f  %6.1f" %
          (fr["off"], len(b), len(ts), O, sc, second, sc - second, O % 4096, O % 16, zero, cm))

json.dump(res, open(os.path.join(HERE, "findO.json"), "w"), indent=1)
print("\nsummary: median score %.1f, median control %.1f, median (best-second) %.1f" % (
    sorted(r["score"] for r in res)[len(res) // 2],
    sorted(r["ctrl"] for r in res)[len(res) // 2],
    sorted(r["score"] - r["second"] for r in res)[len(res) // 2]))
