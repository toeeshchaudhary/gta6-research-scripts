"""Task 2d: locate the hash slots of script.rpf's table and try to resolve them.

A slot is 16 bytes: [u32 key][u32 0][u32 next_off][u32 0x71717171], with next_off either 0 or a
forward image offset. Report the key population, and resolve keys against the joaat dictionary.
"""
import os, sys, struct, collections
import numpy as np

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
BLOB = os.path.join(OUT, "script_rpf_image.bin")
FILL = 0x71717171

def joaat(s: str) -> int:
    h = 0
    for c in s.lower().encode("latin-1", "replace"):
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF

def slots(b):
    n = len(b)
    out = []
    for o in range(4, n - 20, 4):
        if struct.unpack_from("<I", b, o + 4)[0] != 0: continue
        if struct.unpack_from("<I", b, o + 12)[0] != FILL: continue
        nx = struct.unpack_from("<I", b, o + 8)[0]
        if nx != 0 and not (0x100 <= nx < n): continue
        out.append((o, struct.unpack_from("<I", b, o)[0], nx))
    return out

def main():
    b = open(BLOB, "rb").read()
    sl = slots(b)
    print(f"slot-shaped positions: {len(sl):,}")
    keys = collections.Counter(k for _, k, _ in sl)
    print(f"distinct keys: {len(keys):,}  zero keys: {keys.get(0,0)}")
    d = {}
    for line in open(os.path.join(OUT, "strings_all.txt"), encoding="utf-8"):
        s = line.split("\t", 1)[0]
        if s: d.setdefault(joaat(s), s)
    for s in open(os.path.join(OUT, "missions_common_rpf.txt"), encoding="utf-8"):
        s = s.strip()
        if s: d.setdefault(joaat(s), s)
    print(f"dictionary: {len(d):,} hashes")
    hit = [(o, k, d[k]) for o, k, _ in sl if k in d]
    print(f"resolved keys: {len(hit):,} / {len(sl):,}  = {100*len(hit)/max(1,len(sl)):.1f}%")
    hit.sort(key=lambda x: x[0])
    with open(os.path.join(OUT, "s6_slots.txt"), "w", encoding="utf-8") as f:
        for o, k, s in hit:
            f.write(f"{o:08x}\t{k:08x}\t{s}\n")
    for o, k, s in hit[:120]:
        print(f"   {o:#08x} 0x{k:08x} {s[:80]}")
    # structural sanity: how many slots chain forward, chain lengths
    chained = sum(1 for _, _, nx in sl if nx)
    print(f"slots with a next pointer: {chained:,}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
