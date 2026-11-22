"""step4_sweep.py - where does the logical stream continue after a chunk ends?

For each decoded chunk: sweep s = 0..64 bytes past the stream end and try
  raw deflate / zlib-framed, with dict = last 32 KiB of the plaintext so far, or zeros.
Also try the continuation anchored at the stream end's align16 (+0/8/12/16).
"""
import json, os, sys, zlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stitchlib as S

HERE = os.path.dirname(os.path.abspath(__file__))
D = S.data()
meta = sorted(json.load(open(os.path.join(HERE, "streams_meta.json"))), key=lambda s: s["off"])


def plaintext(off):
    for fam, d in (("exact", r"work\codec\full\exact"), ("zd", r"work\codec\full\zeros_dict_unverified")):
        p = os.path.join(S.ROOT, d, "%s_%08X.bin" % (fam, off))
        if os.path.exists(p):
            return open(p, "rb").read()
    r = S.inflate(off)
    return r["out"] if r else b""


def try_raw(off, zdict):
    d = zlib.decompressobj(-15, zdict=zdict)
    out = bytearray(); pos = off
    try:
        while pos < S.REGION_END and not d.eof:
            chunk = D[pos:min(S.REGION_END, pos + 65536)]
            pos += len(chunk); out += d.decompress(chunk)
        out += d.flush()
    except zlib.error:
        return None
    if not d.eof or len(out) < 256:
        return None
    return len(out)


hits = collections.Counter()
detail = []
for s in meta:
    pt = plaintext(s["off"])
    tail = (b"\x00" * 32768 + pt)[-32768:]
    best = None
    for s_off in range(0, 65):
        for name, zd in (("prev", tail), ("zero", b"\x00" * 32768)):
            n = try_raw(s["end"] + s_off, zd)
            if n:
                hits[(name, s_off)] += 1
                if best is None or n > best[2]:
                    best = (name, s_off, n)
    if best:
        detail.append((s["off"], s["end"], best))

print("succcesses by (dict, skip):")
for k, v in hits.most_common(20):
    print("   ", k, v)
print("\ntotal streams with any continuation: %d of %d" % (len(detail), len(meta)))
for d in detail[:25]:
    print("   0x%08X end 0x%08X best %s skip %d out %d" % d)
