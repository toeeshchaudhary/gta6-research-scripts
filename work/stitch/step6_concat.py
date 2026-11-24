"""step6_concat.py - test the O=0 model.

Model: a pointer-rich chunk is the HEAD of a resource (record array at offset 0, count at +0x08,
base 0x50000000 => resource-relative offsets). Its pointers name arrays at HIGHER offsets, i.e.
material that comes AFTER it in the same resource. So the resource's remaining plaintext must be
the following chunks. Build candidate resources by appending following decoded chunks in archive
order and check whether the bytes at the pointer targets become array-shaped.
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


def is_records(b):
    """head looks like a records chunk: u64 0 at 0, count in u32 at 4, hash at 0x10"""
    if len(b) < 0x30:
        return False
    return struct.unpack_from("<Q", b, 0)[0] == 0 and 0 < struct.unpack_from("<I", b, 8)[0] < 100000


def asc_score(b, p, n=6):
    """how array-like are the 4-byte words at b[p:] ?  -> fraction of strictly ascending small values"""
    if p < 0 or p + 4 * n > len(b):
        return 0.0
    v = struct.unpack_from("<%dI" % n, b, p)
    if any(x > 0x1000000 for x in v):
        return 0.0
    up = sum(1 for i in range(n - 1) if v[i + 1] > v[i])
    return up / (n - 1)


cands = [(s["off"], plaintext(s["off"])) for s in meta]
size = {o: len(b) for o, b in cands}
print("chunks: %d, %d B" % (len(cands), sum(size.values())))

# which chunks look like resource heads?
heads = [(o, b) for o, b in cands if is_records(b)]
print("record-head chunks: %d" % len(heads))

idx = [o for o, _ in cands]
pos = {o: i for i, o in enumerate(idx)}

print("\n=== structure at pointer targets when the chunk is placed at base 0 and followed by "
      "subsequent chunks (archive order) ===")
print("  head       size   nptr  maxtarget  need   chunks  got    frac<got  asc@targets")
report = []
for o, b in heads[:14]:
    ptrs = sorted(t for _, _, t in S.ptr_offsets(b))
    if len(ptrs) < 8:
        continue
    need = ptrs[-1] + 0x88
    i = pos[o]
    buf = b
    j = i + 1
    while len(buf) < need and j < len(idx):
        buf += cands[j][1]
        j += 1
    got = len(buf)
    frac = sum(1 for t in ptrs if t < got) / len(ptrs)
    asc = sum(asc_score(buf, t) for t in ptrs[:40]) / min(40, len(ptrs))
    report.append((o, len(b), len(ptrs), ptrs[-1], need, j - i, got, frac, asc))
    print("  0x%08X %6d %5d  0x%06X %7d  %5d %7d   %.3f     %.2f" %
          (o, len(b), len(ptrs), ptrs[-1], need, j - i, got, frac, asc))

print("\n=== hexdump of the target region for the first head (base 0 model) ===")
if report:
    o = report[0][0]
    b = dict(cands)[o]
    ptrs = sorted(t for _, _, t in S.ptr_offsets(b))
    need = ptrs[-1] + 0x88
    i = pos[o]
    buf = b
    j = i + 1
    while len(buf) < need and j < len(idx):
        buf += cands[j][1]
        j += 1
    t0 = ptrs[0]
    print("  first target 0x%X ; 96 bytes there:" % t0)
    print(S.dump_at(buf, t0 - 16, 112))
