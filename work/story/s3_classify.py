"""Task 2: classify every readable inflate in script.rpf / common.rpf / story000_script.rpf
(and summarise data.rpf) into container families, and name the fraction of each archive.
"""
import os, sys, re, json, collections, hashlib

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
W = lambda *a: os.path.join(B, "work", "lineage", "bin", "Release", "net8.0", *a)
CORP = [("script", W("out_script")), ("common", W("out_common")), ("story", W("out_story"))]

TAGS = [b"PSIN", b"LSCH", b"LENM", b"LSNS", b"LGID", b"LRSC", b"CHKS"]

def psin_chain(b):
    """walk the PSIN chunk chain; return (tags_ok, end, declared) or None"""
    if not b.startswith(b"PSIN"): return None
    off = 0; tags = []
    while off + 8 <= len(b):
        tag = b[off:off+4]
        ln = int.from_bytes(b[off+4:off+8], "big")
        if tag not in TAGS: return ("bad-tag", off, tag)
        tags.append(tag.decode())
        off += ln
        if ln < 8: return ("short", off, tag)
    return ("exact" if off == len(b) else "over", off, len(tags))

def classify(b):
    n = len(b)
    head = b[:16]
    if b.startswith(b"PSIN"):
        c = psin_chain(b)
        return "PSIN", c
    if b.startswith(b"RBF0"): return "RBF0", None
    if b.startswith(b"<?xm"): return "XML", None
    if b.startswith(b"DXBC"): return "DXBC", None
    if b[:8] == b"\0"*8: return "zeros8", None
    if b[:4] == b"\0"*4: return "zeros4", None
    # printable fraction of first 4 KiB
    s = b[:4096]
    pr = sum(1 for x in s if 32 <= x < 127) / max(1, len(s))
    if pr > 0.9: return "TEXT", None
    return "bin:" + head[:4].hex(), None

def main():
    rows = []
    for arch, d in CORP:
        cnt = collections.Counter()
        totb = 0
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if not os.path.isfile(p): continue
            b = open(p, "rb").read()
            totb += len(b)
            kind, extra = classify(b)
            cnt[kind] += 1
            # utf16 detection
            u16 = b[:200].count(b"\0")
            rows.append((arch, fn, len(b), kind, str(extra), b[:16].hex(), u16))
        print(f"\n=== {arch}.rpf inflates: {sum(cnt.values())} files, {totb:,} bytes")
        for k, v in cnt.most_common(40):
            bb = sum(r[2] for r in rows if r[0] == arch and r[3] == k)
            print(f"   {k:14s} n={v:6d} bytes={bb:,}")
    import csv
    with open(os.path.join(OUT, "s3_classify.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archive", "file", "size", "kind", "extra", "head16", "nulFirst200"])
        w.writerows(rows)
    # PSIN chain completeness
    for arch, d in CORP:
        exact = over = bad = 0
        for r in rows:
            if r[0] == arch and r[3] == "PSIN":
                e = r[4]
                if "'exact'" in e: exact += 1
                elif "'over'" in e: over += 1
                else: bad += 1
        print(f"{arch}: PSIN chain exact={exact} over={over} bad/short={bad}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
