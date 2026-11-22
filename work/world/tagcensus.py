"""Census of resource type tags.

Many GTA VI RPF9 resource system blobs carry a 4-byte ASCII tag at +0x10 of the
decompressed system block. Inflate a small prefix of every candidate and tally it.
No writes to the game directory.
"""
import collections
import sys
import zlib

arch = sys.argv[1]
lst = sys.argv[2]
limit = int(sys.argv[3])

TAGS = collections.Counter()
SAMPLES = {}
bad = 0
ok = 0

with open(arch, "rb", buffering=0) as f:
    for n, line in enumerate(open(lst)):
        if n >= limit:
            break
        off = int(line.strip(), 16)
        f.seek(off)
        d = zlib.decompressobj()
        try:
            head = d.decompress(f.read(4096), 512)
        except Exception:
            bad += 1
            continue
        if len(head) < 0x18:
            bad += 1
            continue
        ok += 1
        tag = head[0x10:0x14]
        key = tag.decode("latin-1") if all(32 <= c < 127 for c in tag) else "----"
        # also record the u64 at 0 and 8 to see the header shape
        TAGS[key] += 1
        if key not in SAMPLES:
            SAMPLES[key] = (off, head[:0x50].hex())

print(f"probed={ok} fail={bad}")
for key, count in TAGS.most_common(40):
    off, hx = SAMPLES[key]
    print(f"{count:7d}  tag={key!r:10}  first=0x{off:X}  {hx}")
