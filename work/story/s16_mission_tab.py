"""Task 1e: does an already-read blob hold a *compiled* mission table?

Blob: work\lineage\bin\Release\net8.0\out_story\04a38c40_67398.bin (PSIN container, 67,398 B)
- resolve every u64/u32 against joaat(mission ids) and the corpus dictionary
- look for the class constants seen around those hits and for a repeating record shape
Also tests alternative hash functions for the mission ids.
"""
import os, sys, struct, collections, zlib

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
BLOB = os.path.join(B, "work", "lineage", "bin", "Release", "net8.0", "out_story", "04a38c40_67398.bin")

def joaat(s, seed=0):
    h = seed
    for c in s.lower().encode():
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF

def variants(name):
    yield "joaat", joaat(name)
    yield "joaat_seedB779", joaat(name, 0xB779A091)
    yield "joaat_seed3FAC", joaat(name, 0x3FAC7125)
    yield "joaat_upper_source", joaat(name.upper())
    yield "crc32", zlib.crc32(name.encode()) & 0xFFFFFFFF
    yield "fnv1a", __import__("functools").reduce(
        lambda h, c: ((h ^ c) * 0x01000193) & 0xFFFFFFFF, name.encode(), 0x811C9DC5)

def main():
    missions = [x.strip() for x in open(os.path.join(OUT, "missions_common_rpf.txt")) if x.strip()]
    b = open(BLOB, "rb").read()
    print(f"blob {len(b):,} B")
    for fn, gen in (("mission-id", None),):
        pass
    tabs = collections.defaultdict(dict)
    for m in missions:
        for k, v in variants(m):
            tabs[k][v] = m
    for k in tabs:
        found = [h for h in tabs[k] if struct.pack("<I", h) in b]
        print(f"hash fn {k:18s}: {len(found):3d} of {len(tabs[k])} present")
        for h in found[:6]:
            i = b.find(struct.pack("<I", h))
            print(f"    {tabs[k][h]:28s} 0x{h:08x} at {i:#x}")
    # structure around the two known hits
    for i in (0xE760, 0xF350, 0xF060, 0xFC50):
        print(f"\n-- context {i:#x}")
        for j in range(i - 48, i + 48, 16):
            print(f"  {j:06x} " + b[j:j+16].hex(" ") + " |" +
                  "".join(chr(c) if 32 <= c < 127 else "." for c in b[j:j+16]) + "|")
    # u32 census: how many dwords repeat (table-like) in this blob
    w = struct.unpack_from("<%dI" % (len(b) // 4), b, 0)
    c = collections.Counter(w)
    rep = [(k, v) for k, v in c.items() if v > 3]
    print(f"\nrepeated dwords (>3x): {len(rep)}; top {[(hex(k), v) for k, v in sorted(rep, key=lambda x: -x[1])[:8]]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
