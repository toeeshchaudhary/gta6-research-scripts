"""step1_recon.py - enumerate every 16-aligned zlib stream in the program region,
then test the stitching hypothesis directly: does align16(end of stream i) equal the
start of stream j?

Writes streams.json (all decoded streams with offsets/ends) and prints the census.
"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stitchlib as S

D = S.data()
lo, hi = S.REGION_START, S.REGION_END

# --- candidate 78 DA positions at 16-aligned offsets --------------------------------
cands = []
pos = D.find(b"\x78\xda", lo)
while 0 <= pos < hi:
    if pos % 16 == 0:
        cands.append(pos)
    pos = D.find(b"\x78\xda", pos + 1)
print("16-aligned 78DA candidates in region: %d" % len(cands))

streams = []
for off in cands:
    r = S.inflate(off)
    if r and len(r["out"]) >= 64:
        streams.append(r)
streams.sort(key=lambda s: s["off"])
print("decoded streams (>=64 B): %d, total out %d" % (len(streams), sum(len(s["out"]) for s in streams)))

fam = collections.Counter(s["mode"] for s in streams)
print("decode modes:", dict(fam))
sz = [len(s["out"]) for s in streams]
print("output size: min %d med %d max %d" % (min(sz), sorted(sz)[len(sz) // 2], max(sz)))

# --- which blocks do they fall in? --------------------------------------------------
blocks = S.blocks()
print("carved blocks: %d" % len(blocks))
bidx = {}
for i, (b, st, ln) in enumerate(blocks):
    bidx[st] = (i, ln)


def block_of(off):
    for i, st, ln in blocks:
        if st <= off < st + ln:
            return i, st, ln
    return None


# --- adjacency census ---------------------------------------------------------------
print("\n=== continuity census: gap between align16(prev.stream end) and next stream start ===")
gaps = collections.Counter()
pairs = []
for a, b in zip(streams, streams[1:]):
    gap = b["off"] - S.align16(a["end"])
    gaps[gap] += 1
    pairs.append((a, b, gap))
print("top gaps:", gaps.most_common(12))
contig = [(a, b) for a, b, g in pairs if g == 0]
print("exactly-contiguous pairs (gap==0): %d" % len(contig))
for a, b in contig[:20]:
    print("   0x%08X end 0x%08X out %6d  ->  0x%08X" % (a["off"], a["end"], len(a["out"]), b["off"]))

print("\n=== gap distribution restricted to streams inside the same carved block ===")
same = collections.Counter()
for a, b, g in pairs:
    ba, bb = block_of(a["off"]), block_of(b["off"])
    same[(ba[0] if ba else None) == (bb[0] if bb else None), g == 0] += 1
print(dict(same))

# --- how far does each stream sit from its block end? --------------------------------
print("\n=== distance from stream end to block end (align4k) ===")
d = collections.Counter()
for s in streams:
    bi = block_of(s["off"])
    if bi:
        i, st, ln = bi
        bend = S.align4k(st + ln) if st + ln > st else st + ln
        d[(st + ln) - s["end"] if (st + ln) > s["end"] else -1] += 1
print("trailing-bytes buckets (block_end - stream_end):", d.most_common(10))

json.dump([{k: (v if k != "out" else None) for k, v in s.items()} for s in streams],
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "streams_meta.json"), "w"), indent=1)
