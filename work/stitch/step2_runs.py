"""step2_runs.py - build page-runs (the "page stitching" chains) from the carved block map
and measure the alignment evidence for each join.

Join rule tested:
   tight  : next.start == align16(prev.start + prev.dataLen)      -> same page, continuation
   page   : next.start == align4k(prev.start + prev.dataLen)      -> resource boundary
Everything else is "gap" and is reported.

Writes runs.json.
"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stitchlib as S

HERE = os.path.dirname(os.path.abspath(__file__))
blocks = sorted(S.blocks(), key=lambda b: b[1])
print("blocks: %d, first 0x%X last 0x%X+%d" % (len(blocks), blocks[0][1], blocks[-1][1], blocks[-1][2]))

kinds = collections.Counter()
joins = []
for a, b in zip(blocks, blocks[1:]):
    sa, la = a[1], a[2]
    ea = sa + la
    sb = b[1]
    t = S.align16(ea)
    p = S.align4k(ea)
    if sb == t and sb == p:
        k = "both(tight==page)"
    elif sb == t:
        k = "tight"
    elif sb == p:
        k = "page"
    else:
        k = "gap"
    kinds[k] += 1
    joins.append(k)
print("join kinds:", dict(kinds))

gaps = [b[1] - S.align16(a[1] + a[2]) for a, b in zip(blocks, blocks[1:]) if
        b[1] != S.align16(a[1] + a[2]) and b[1] != S.align4k(a[1] + a[2])]
if gaps:
    gaps.sort()
    print("unexplained gaps: n=%d min %d med %d max %d" % (len(gaps), gaps[0], gaps[len(gaps) // 2], gaps[-1]))
    print("  gap %% 16 histogram:", collections.Counter(g % 16 for g in gaps).most_common())
    print("  smallest 12:", gaps[:12])

# --- runs -------------------------------------------------------------------------
runs = []
cur = [blocks[0]]
for k, (a, b) in zip(joins, zip(blocks, blocks[1:])):
    if k.startswith("tight"):
        cur.append(b)
    else:
        runs.append(cur)
        cur = [b]
runs.append(cur)
print("\nruns: %d   sizes: %s" % (len(runs), collections.Counter(len(r) for r in runs).most_common(8)))
print("runs with >1 block: %d, bytes in them: %d" %
      (sum(1 for r in runs if len(r) > 1), sum(r[-1][1] + r[-1][2] - r[0][1] for r in runs if len(r) > 1)))

# stream assignment
streams = json.load(open(os.path.join(HERE, "streams_meta.json")))
streams.sort(key=lambda s: s["off"])


def run_of(off):
    for i, r in enumerate(runs):
        if r[0][1] <= off < r[-1][1] + r[-1][2]:
            return i
    return None


per_run = collections.Counter()
res = []
for i, r in enumerate(runs):
    lo, hi = r[0][1], r[-1][1] + r[-1][2]
    ss = [s for s in streams if lo <= s["off"] < hi]
    per_run[len(ss)] += 1
    res.append({"run": i, "start": lo, "end": hi, "span": hi - lo, "nblocks": len(r),
                "blocks": [b[1] for b in r], "streams": [s["off"] for s in ss],
                "out_bytes": sum(0 for s in ss)})
print("\nstreams per run:", dict(per_run))
tot_streams = sum(len(x["streams"]) for x in res)
print("streams assigned to runs: %d of %d" % (tot_streams, len(streams)))

json.dump({"joins": kinds, "runs": res}, open(os.path.join(HERE, "runs.json"), "w"), indent=1)

# --- how do streams relate to run boundaries? --------------------------------------
print("\n=== streams vs run extent ===")
c = collections.Counter()
for x in res:
    for so in x["streams"]:
        c[(so - x["start"], x["end"] - so, len(x["streams"]))] += 1
print("(stream_off - run_start, run_end - stream_off, nstreams_in_run) top 12:")
for k, v in c.most_common(12):
    print("   ", k, v)

print("\n=== biggest runs ===")
for x in sorted(res, key=lambda x: -x["span"])[:10]:
    print("  run %3d  0x%08X..0x%08X  span %7d  blocks %2d  streams %s" %
          (x["run"], x["start"], x["end"], x["span"], x["nblocks"], x["streams"]))
