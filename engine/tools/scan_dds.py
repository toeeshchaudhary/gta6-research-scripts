import struct, sys
from pathlib import Path
from collections import Counter
root = Path(r".\work\assets")
fmtcount = Counter(); fmtn = {}
bad = 0; n = 0
for p in root.rglob("*.dds"):
    n += 1
    d = p.open("rb").read(148)
    if len(d) < 148 or d[:4] != b"DDS ": bad += 1; continue
    fourcc = d[84:88]
    if fourcc == b"DX10":
        fmt = struct.unpack_from("<I", d, 128)[0]
    else:
        fmt = "legacy:" + repr(fourcc) + "/" + struct.pack("<I", struct.unpack_from("<I", d, 80)[0]).hex()
    h, w = struct.unpack_from("<II", d, 12)
    fmtcount[fmt] += 1
    fmtn.setdefault(fmt, (p.name, w, h))
print("total dds:", n, "bad:", bad)
for k, v in fmtcount.most_common():
    ex = fmtn[k]
    print(f"  fmt {k}: {v}  e.g. {ex[0]} {ex[1]}x{ex[2]}")
