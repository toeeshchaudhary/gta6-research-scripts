"""Task 2c/1c: resolve u32 hashes inside a target blob against a joaat dictionary built from
every string harvested out of the readable corpus (and the mission-id list).

Usage: s5_hashresolve.py <blob> [<blob> ...]
"""
import os, sys, collections, struct
import numpy as np

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")

def joaat(s: str) -> int:
    h = 0
    for c in s.lower().encode("latin-1", "replace"):
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF

def build_dict():
    d = {}
    with open(os.path.join(OUT, "strings_all.txt"), encoding="utf-8") as f:
        for line in f:
            s = line.split("\t", 1)[0]
            if not s: continue
            d.setdefault(joaat(s), s)
    for name, path in (("missions", os.path.join(OUT, "missions_common_rpf.txt")),):
        for s in open(path, encoding="utf-8"):
            s = s.strip()
            if s: d.setdefault(joaat(s), s)
    return d

def scan(path, d):
    b = open(path, "rb").read()
    a = np.frombuffer(b, dtype=np.uint8)
    n = len(a) - 3
    v = (a[0:n].astype(np.uint32) | (a[1:n+1].astype(np.uint32) << 8)
         | (a[2:n+2].astype(np.uint32) << 16) | (a[3:n+3].astype(np.uint32) << 24))
    want = np.fromiter(d.keys(), dtype=np.uint32, count=len(d))
    m = np.isin(v, want)
    idx = np.nonzero(m)[0]
    print(f"{os.path.basename(path)}: {len(b):,} bytes, {len(idx):,} hash hits")
    res = []
    for i in idx[:400]:
        val = int(v[i])
        res.append((i, val, d[val]))
        print(f"   {i:#08x} 0x{val:08x} {d[val]}")
    return res

def main():
    d = build_dict()
    print(f"dictionary hashes: {len(d):,}")
    for p in sys.argv[1:]:
        scan(p, d)
    return 0

if __name__ == "__main__":
    sys.exit(main())
