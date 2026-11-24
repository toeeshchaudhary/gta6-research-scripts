"""step7_hdr.py - is the decoded (plaintext) size of a chunk recorded in the 8-byte entry
header that precedes it?  If yes, every chunk's absolute plaintext offset is computable and the
'fragment base O' becomes arithmetic instead of guesswork.
"""
import json, os, sys, struct, collections
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


print("entry header = 8 bytes at payload-8 (payload = align16(entry_off+8), usually a 4K page + 16)")
print("  stream    payload   outlen   comp   hdr[payload-8 .. payload-1]           cands(eq outlen)")
rows = []
for s in meta:
    out = plaintext(s["off"])
    off = s["off"]
    comp = s["cons"]
    hdr8 = D[off - 8:off]
    hdr16 = D[off - 16:off]
    eq = []
    for base in (off - 8, off - 16):
        for w in range(2, 9):
            for k in range(0, 16 - w + 1):
                for endian in ("<", ">"):
                    h = D[base + k:base + k + w]
                    if len(h) != w:
                        continue
                    v = int.from_bytes(h, "little" if endian == "<" else "big")
                    for name, target in (("out", len(out)), ("out/16", len(out) // 16), ("comp", comp)):
                        if v == target and v > 64:
                            eq.append("%s@%+d w%d %s" % (name, base + k - off, w, endian))
    rows.append((off, len(out), comp, hdr8.hex(" "), eq))

for r in rows[:40]:
    print("0x%08X 0x%08X %6d %6d  %-24s %s" % (r[0], r[0], r[1], r[2], r[3], ", ".join(r[4][:3])))

print("\ntotal with any header field == outlen: %d of %d" % (sum(1 for r in rows if r[4]), len(rows)))

# --- also: does any u16/u32 at payload-8 (the tag area) repeat per output-length class?
print("\n=== tag (u16 at entry header) frequency, and mean plaintext size per tag ===")
byt = collections.defaultdict(list)
for s in meta:
    out = plaintext(s["off"])
    t = struct.unpack_from("<H", D, s["off"] - 8)[0]
    byt[t].append(len(out))
for t, v in sorted(byt.items(), key=lambda kv: -len(kv[1]))[:20]:
    print("   tag 0x%04X  n=%2d  outsizes %s" % (t, len(v), sorted(v)[:6]))

# --- entry header chain: what sits 8 bytes before each payload? ---------------------
print("\n=== 8-byte entry headers of all 905 blocks (first 24), with page alignment ===")
blocks = sorted(S.blocks(), key=lambda b: b[1])
for i, st, ln in blocks[:24]:
    pay = S.align16(st + 8)
    print("   blk@0x%08X page+%3d  hdr %s  payload 0x%08X %s  next 0x%08X" %
          (st, st % 4096, D[st:st + 8].hex(" "), pay,
           "78DA" if D[pay:pay + 2] == b"\x78\xda" else D[pay:pay + 2].hex(),
           blocks[i + 1][1] if i + 1 < len(blocks) else 0))
