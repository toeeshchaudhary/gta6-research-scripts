"""step9_hashjoin.py - can a chunk's record identities be found in another chunk?

Records carry a 64-bit hash at +0x10 and a 32-bit value at +0x18. If children / arrays of these
records live in another chunk (as the base-O analysis implies), their hashes should appear there
as data words. That would give a direct, checkable chunk->chunk join plus the base offset.
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


corpus = {s["off"]: plaintext(s["off"]) for s in meta}
print("corpus: %d chunks, %d B" % (len(corpus), sum(len(b) for b in corpus.values())))

# hash multiset of every chunk, at 8-byte alignment
h64 = collections.defaultdict(set)
for off, b in corpus.items():
    for p in range(0, len(b) - 8, 8):
        v = struct.unpack_from("<Q", b, p)[0]
        if v > 0x10000000000:            # hash-like: high bits set
            h64[v].add(off)

print("distinct 64-bit hash-like words: %d" % len(h64))

# for each chunk: how many of its record hashes appear in ANOTHER chunk?
print("\n  chunk      nrec  hashes  found_elsewhere  of_which_in_one_chunk")
tot = 0
for off, b in corpus.items():
    nrec = len(b) // 0x88
    if nrec < 4:
        continue
    hs = [struct.unpack_from("<Q", b, k * 0x88 + 0x10)[0] for k in range(nrec)]
    hs = [h for h in hs if h > 0x10000000000]
    hits = [(h, h64[h] - {off}) for h in hs if len(h64[h]) > 1]
    if hits:
        others = collections.Counter(o for _, s in hits for o in s)
        tot += 1
        print("  0x%08X %5d %6d  %6d            %s" % (off, nrec, len(hs), len(hits),
                                                      others.most_common(3)))
print("chunks with cross-chunk hash hits: %d" % tot)

# --- 32-bit side: joaat-style values at +0x18 -------------------------------------
print("\n=== 32-bit values at record+0x18: cross-chunk hits ===")
h32 = collections.defaultdict(set)
for off, b in corpus.items():
    for p in range(0, len(b) - 4, 4):
        v = struct.unpack_from("<I", b, p)[0]
        h32[v].add(off)
tot = 0
for off, b in corpus.items():
    nrec = len(b) // 0x88
    if nrec < 4:
        continue
    vs = [struct.unpack_from("<I", b, k * 0x88 + 0x18)[0] for k in range(nrec)]
    vs = [v for v in vs if v != 0]
    hits = [v for v in vs if len(h32[v]) > 1]
    if hits:
        tot += 1
print("chunks with cross-chunk 32-bit hits: %d of %d" % (tot, len(corpus)))

# --- do the pointer TARGET offsets themselves appear as u32 data anywhere? --------
print("\n=== are pointer target offsets present as data words in the corpus? ===")
allw32 = set()
for b in corpus.values():
    for p in range(0, len(b) - 4, 4):
        allw32.add(struct.unpack_from("<I", b, p)[0])
print("distinct u32 words: %d" % len(allw32))
for off, b in list(corpus.items())[:8]:
    ts = sorted({t for _, _, t in S.ptr_offsets(b)})
    if not ts:
        continue
    inter = [t for t in ts if t in allw32]
    print("  0x%08X  %4d targets, %4d present as u32 data words (%.1f%%)" %
          (off, len(ts), len(inter), 100.0 * len(inter) / len(ts)))
