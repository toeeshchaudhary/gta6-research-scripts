import struct
from pathlib import Path
for p in Path(r"./work/assets/textures").rglob("*.dds"):
    n=p.stem
    if "texture_0000" in n or "texture_0" in n: continue
    d=p.open("rb").read(148)
    fmt=struct.unpack_from("<I",d,128)[0]
    h,w=struct.unpack_from("<II",d,12)
    print(f"{fmt:3d} {w:5d}x{h:<5d} {p.stat().st_size:9d} {n}")
