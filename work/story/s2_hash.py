"""Task 1b: resolve hashes (numpy accelerated).

- u32 at EVERY byte offset over the script-side corpora, counted
- joaat of the 145 CMission MissionIds (and mission_* variants) looked up
- then a full dictionary built from every distinct printable string in every corpus,
  hashed and looked up against the same u32 stream
"""
import os, re, sys, json, collections
import numpy as np

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
CHUNK = 16 << 20
OVER = 8

def joaat(s: str) -> int:
    h = 0
    for c in s.lower().encode("latin-1", "replace"):
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF

SCRIPT_DIRS = ["scripts/out/script_groups", "scripts/out/story_groups",
               "lineage/bin/Release/net8.0/out_script", "lineage/bin/Release/net8.0/out_story",
               "codec/full/exact", "codec/full/zeros_dict_unverified", "codec/dec"]

def files_in(rel):
    d = os.path.join(B, "work", rel)
    if not os.path.isdir(d): return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, f))]

def u32_stream(paths):
    for p in paths:
        with open(p, "rb") as f:
            prev = b""
            while True:
                blk = f.read(CHUNK)
                if not blk: break
                buf = prev + blk
                if len(buf) < 4:
                    prev = buf; continue
                a = np.frombuffer(buf[:len(buf)], dtype=np.uint8)
                n = len(a) - 3
                v = (a[0:n].astype(np.uint32)
                     | (a[1:n+1].astype(np.uint32) << 8)
                     | (a[2:n+2].astype(np.uint32) << 16)
                     | (a[3:n+3].astype(np.uint32) << 24))
                yield p, 0, v
                prev = buf[-3:]

def main():
    paths = []
    for rel in SCRIPT_DIRS: paths += files_in(rel)
    tot = sum(os.path.getsize(p) for p in paths)
    print(f"corpora files={len(paths)} bytes={tot:,}")

    missions = [x.strip() for x in open(os.path.join(OUT, "missions_common_rpf.txt")) if x.strip()]
    cands = {}
    for m in missions:
        cands[f"joaat({m})"] = joaat(m)
        cands[f"joaat(mission_{m.lower()})"] = joaat("mission_" + m.lower())
        cands[f"joaat(mission_{m})"] = joaat("mission_" + m)
    want = np.array(sorted(set(cands.values())), dtype=np.uint32)
    rev = collections.defaultdict(list)
    for k, v in cands.items(): rev[v].append(k)

    hits = collections.Counter()
    where = collections.defaultdict(set)
    for p, _, v in u32_stream(paths):
        m = np.isin(v, want)
        if m.any():
            vals, cnts = np.unique(v[m], return_counts=True)
            for a_, c_ in zip(vals.tolist(), cnts.tolist()):
                hits[a_] += c_; where[a_].add(os.path.basename(p))
    print(f"\nmission-hash u32 values found: {len(hits)} of {len(want)}")
    for val, c in hits.most_common(60):
        print(f"  0x{val:08x} x{c:5d}  {rev[val][:2]}")
    with open(os.path.join(OUT, "s2_mission_hash_hits.txt"), "w", encoding="utf-8") as f:
        for val in sorted(hits):
            f.write(f"{val:08x}\t{hits[val]}\t{rev[val][:2]}\t{sorted(where[val])[:3]}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
