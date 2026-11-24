"""Verify every far-away class-S row against its raw record bytes.

A genuine placement record has a yaw in [0x0C] within +-pi and an archetype hash at [0x2C] that is
not a float bit pattern. A record from a float/geometry family has neither. Each far row is looked
up by its exact position triple in the inflated resource.

usage: python -I farverify.py <levels.rpf> <scene.json> <report.json> [far_units]
"""
import collections
import json
import math
import struct
import sys
import zlib

lv, scene, report = sys.argv[1:4]
FAR = int(sys.argv[4]) if len(sys.argv) > 4 else 15000
inst = json.load(open(scene, encoding="utf-8"))["instances"]
S = [i for i in inst if i.get("class") == "S"]
far = [i for i in S if max(abs(i["pos"][0]), abs(i["pos"][1])) > FAR]
print(f"far rows {len(far)}")


def cf(v):
    f = struct.unpack("<f", struct.pack("<I", v))[0]
    return f == f and 0.01 <= abs(f) <= 20000.0


byres = collections.defaultdict(list)
for i in far:
    byres[i["resource"]].append(i)

res_ok = res_bad = 0
ok = bad = 0
noflt = 0
ok_examples = []
bad_examples = []
for res, rows in byres.items():
    off = int(res, 16)
    try:
        with open(lv, "rb") as f:
            f.seek(off)
            blob = zlib.decompressobj().decompress(f.read(3_000_000))
    except Exception:
        continue
    idx = {}
    i = 0x90
    while i + 0x70 <= len(blob):
        t = struct.unpack_from("<3f", blob, i)
        idx[(round(t[0], 3), round(t[1], 3), round(t[2], 3))] = i
        i += 80
    r_ok = r_bad = 0
    for row in rows:
        key = (round(row["pos"][0], 3), round(row["pos"][1], 3), round(row["pos"][2], 3))
        at = idx.get(key)
        if at is None:
            bad += 1
            r_bad += 1
            continue
        yaw = struct.unpack_from("<f", blob, at + 0x0C)[0]
        h = struct.unpack_from("<I", blob, at + 0x2C)[0]
        good = abs(yaw) <= 3.2 and not cf(h)
        if good:
            ok += 1
            r_ok += 1
            if len(ok_examples) < 15:
                ok_examples.append({"resource": res, "pos": row["pos"], "yaw": round(yaw, 3), "hash": f"0x{h:08x}"})
        else:
            bad += 1
            r_bad += 1
            if len(bad_examples) < 15:
                bad_examples.append({"resource": res, "pos": row["pos"], "yaw": round(yaw, 3), "hash": f"0x{h:08x}"})
    if r_ok and not r_bad:
        res_ok += 1
    elif r_bad:
        res_bad += 1

rep = {"far_units": FAR, "far_rows": len(far), "far_resources": len(byres),
       "genuine_rows": ok, "misread_rows": bad, "unmatched_rows": len(far) - ok - bad,
       "genuine_frac": round(ok / len(far), 4) if far else 0,
       "resources_all_genuine": res_ok, "resources_with_misread": res_bad,
       "genuine_examples": ok_examples, "misread_examples": bad_examples}
json.dump(rep, open(report, "w", encoding="utf-8"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if not k.endswith("examples")}, indent=1))
