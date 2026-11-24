"""Task 1f: harvest REPEATED aligned u64 hash keys across the whole program-visible corpus.

Real schema/attribute names repeat; random collisions do not. Only keys seen >=3 times are resolved,
which suppresses the ~9,000 chance hits an unfiltered scan produces.
"""
import os, struct, collections

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
DIRS = ["scripts/out/story_groups", "scripts/out/script_groups",
        "coder/out/decoded", "coder/out/harvest", "coder/out/harvest2",
        "codec/full/exact", "codec/full/zeros_dict_unverified", "codec/dec"]

def joaat(s):
    h = 0
    for c in s.lower().encode():
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF

def main():
    keys = collections.Counter()
    files = 0
    for rel in DIRS:
        d = os.path.join(B, "work", rel)
        if not os.path.isdir(d): continue
        for fn in os.listdir(d):
            p = os.path.join(d, fn)
            if not os.path.isfile(p) or fn.endswith(".json"): continue
            b = open(p, "rb").read(); files += 1
            n = len(b) - 16
            for o in range(0, n, 8):
                hi = struct.unpack_from("<I", b, o + 4)[0]
                if hi: continue
                v = struct.unpack_from("<I", b, o)[0]
                if v > 0x2000: keys[v] += 1
    print(f"files={files} distinct small keys={len(keys):,} keys seen>=3={sum(1 for k,v in keys.items() if v>=3):,}")
    rep = {k: v for k, v in keys.items() if v >= 3}
    d = {}
    for line in open(os.path.join(OUT, "strings_all.txt"), encoding="utf-8"):
        s = line.split("\t", 1)[0]
        if s: d.setdefault(joaat(s), s)
    res = sorted(((v, d[k], k) for k, v in rep.items() if k in d), reverse=True)
    print(f"resolved among them: {len(res)}")
    for v, s, k in res[:120]:
        print(f"   {v:4d} 0x{k:08x} {s[:70]}")
    with open(os.path.join(OUT, "s17_repeated_keys.txt"), "w", encoding="utf-8") as f:
        for v, s, k in res:
            f.write(f"{k:08x}\t{v}\t{s}\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
