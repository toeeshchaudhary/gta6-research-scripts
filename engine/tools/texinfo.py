import struct
from pathlib import Path
for name in ["003_scope.dds","050_ped_dirt_masks.dds","132_ped_skin_wetness_base.dds","000_heightmap.dds","036_light_pollution_map.dds"]:
    for p in Path(r"./work/assets/textures").rglob(name):
        d=p.open("rb").read(148)
        fmt=struct.unpack_from("<I",d,128)[0]; h,w=struct.unpack_from("<II",d,12)
        mips=struct.unpack_from("<I",d,140)[0]
        print(f"{name}: fmt={fmt} {w}x{h} mips={mips} bytes={p.stat().st_size} @ {p.parent.name}")
