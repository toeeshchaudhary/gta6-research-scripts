"""Re-affirm the field map and measure contamination on the complete file.

1. inflate 0x109C363010 (verified class-S street resource) and count the three ARCH.md street
   hashes at the candidate slots: +0x0C, +0x2C, +0x6C (record frame = position base).
2. contamination stats over the complete scene: distinct S hashes vs the name dictionary and vs the
   joaat-proven class-M hash set.

usage: python -I fieldcheck.py <levels.rpf> <scene.json> <names.tsv> <report.json>
"""
import collections
import json
import struct
import sys
import zlib

lv, scene, names, report = sys.argv[1:5]

out = {}

# ---- 1. raw byte re-verification ----
with open(lv, "rb") as f:
    f.seek(0x109C363010)
    raw = f.read(400_000)
d = zlib.decompressobj()
blob = d.decompress(raw)
base = 0x90  # first record, position frame
streets = {0x2F7E64D1: 0, 0xFD378044: 0, 0xD3E22D9A: 0}
for slot in (0x00, 0x0C, 0x2C, 0x6C):
    cnt = {h: 0 for h in streets}
    n = 0
    i = base
    while i + 0x70 <= len(blob):
        v = struct.unpack_from("<I", blob, i + slot)[0]
        if v in cnt:
            cnt[v] += 1
        n += 1
        i += 80
    out[f"slot_{slot:02x}"] = cnt
out["records_in_resource"] = n
out["blob_bytes"] = len(blob)
out["rec0"] = struct.unpack_from("<3f", blob, base)
out["rec0_yaw_0c"] = struct.unpack_from("<f", blob, base + 0x0C)[0]

# ---- 2. contamination in context ----
inst = json.load(open(scene, encoding="utf-8"))["instances"]
dicted = set()
for line in open(names, encoding="utf-8", errors="replace"):
    p = line.split("\t")
    if len(p) >= 2 and p[0].startswith("0x"):
        dicted.add(p[0].lower())
S = [i for i in inst if i.get("class") == "S"]
M = [i for i in inst if i.get("class") == "M"]
mhashes = {i["hash"].lower() for i in M}
sh = collections.Counter(i["hash"].lower() for i in S)
out["s_distinct"] = len(sh)
out["s_instances"] = len(S)
out["s_distinct_named"] = sum(1 for h in sh if h in dicted)
out["s_distinct_also_class_m"] = sum(1 for h in sh if h in mhashes)
out["s_instances_named"] = sum(n for h, n in sh.items() if h in dicted)


def expo(h):
    return (int(h, 16) >> 23) & 0xFF


bands = collections.Counter()
for h in sh:
    bands[expo(h) // 16] += 1
out["s_distinct_by_float_exponent_band"] = {f"0x{k*16:02x}-0x{k*16+15:02x}": v for k, v in sorted(bands.items())}

# wide-float test restricted to coordinate-sized values
def coord_float(h):
    v = struct.unpack("<f", struct.pack("<I", int(h, 16)))[0]
    return v == v and 0.01 <= abs(v) <= 20000.0


out["s_distinct_coord_float_shaped"] = sum(1 for h in sh if coord_float(h))
out["s_distinct_coord_float_and_unnamed"] = sum(1 for h in sh if coord_float(h) and h not in dicted)
out["s_instances_coord_float_shaped"] = sum(n for h, n in sh.items() if coord_float(h))
out["s_instances_coord_float_and_unnamed"] = sum(n for h, n in sh.items() if coord_float(h) and h not in dicted)

# canonical floats (low 16 bits zero) - never a plausible joaat
out["s_distinct_canonical_float"] = sum(1 for h in sh if int(h, 16) & 0xFFFF == 0)

# a real-hash sanity set: hashes that name-resolve
named = [h for h in sh if h in dicted]
out["named_examples"] = named[:10]

json.dump(out, open(report, "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
