"""step10_missions.py - do the recovered records name the 145 known mission ids?

joaat (jenkins one-at-a-time, the GTA name hash) is applied to every id in
work\story\missions_common_rpf.txt, both as-is and upper/lower variants, and the results are
searched for as u32/u64 words in the recovered plaintext. Also tried: the id's hash as the low
32 bits of the 64-bit record hash at +0x10 (i.e. hash64 = some 32-bit prefix + id).
"""
import json, os, sys, struct, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stitchlib as S

HERE = os.path.dirname(os.path.abspath(__file__))
MISS = os.path.join(S.ROOT, r"work\story\missions_common_rpf.txt")


def joaat(s):
    h = 0
    for ch in s.lower().encode("ascii", "replace"):
        h = (h + ch) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


ids = [l.strip() for l in open(MISS) if l.strip()]
print("mission ids: %d" % len(ids))
hashes = {}
for i in ids:
    for name, v in (("joaat", joaat(i)), ("joaat_nohash", joaat(i.replace("_", "")))):
        hashes.setdefault(v, []).append((i, name))
print("distinct hashes: %d" % len(hashes))

meta = sorted(json.load(open(os.path.join(HERE, "streams_meta.json"))), key=lambda s: s["off"])


def plaintext(off):
    for fam, d in (("exact", r"work\codec\full\exact"), ("zd", r"work\codec\full\zeros_dict_unverified")):
        p = os.path.join(S.ROOT, d, "%s_%08X.bin" % (fam, off))
        if os.path.exists(p):
            return open(p, "rb").read()
    r = S.inflate(off)
    return r["out"] if r else b""


hits = []
for s in meta:
    b = plaintext(s["off"])
    for p in range(0, len(b) - 4, 4):
        v = struct.unpack_from("<I", b, p)[0]
        if v in hashes:
            rec = p // 0x88 if p % 0x88 == 0x18 else None
            hits.append((s["off"], p, v, hashes[v], "record+0x18" if rec is not None else "raw",
                         (p % 0x88)))
print("\nraw u32 hits: %d" % len(hits))
seen = set()
for h in hits[:60]:
    key = (h[0], h[2])
    print("  0x%08X +0x%06X  %08X = %-14s %-12s slot+0x%02X" %
          (h[0], h[1], h[2], h[3][0][0], h[3][0][1], h[5]))
print("distinct (chunk,hash) hits: %d" % len(set((x[0], x[2]) for x in hits)))

# same, for the 64-bit record hash: low dword or high dword matching a joaat
print("\n=== record hash64 (+0x10): does either dword equal a joaat of a mission id? ===")
h2 = []
for s in meta:
    b = plaintext(s["off"])
    for k in range(len(b) // 0x88):
        v = struct.unpack_from("<Q", b, k * 0x88 + 0x10)[0]
        lo, hi = v & 0xFFFFFFFF, v >> 32
        for part, val in (("lo", lo), ("hi", hi)):
            if val in hashes:
                h2.append((s["off"], k, v, part, hashes[val][0][0]))
for x in h2[:40]:
    print("  0x%08X rec %3d hash %016X %s = %s" % x)
print("total: %d" % len(h2))
