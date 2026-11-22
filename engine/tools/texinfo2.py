import struct
from pathlib import Path
from PIL import Image
import numpy as np
for name in ["001_clb_heli_earlymorning_aim_guns_pose02_75mm.dds","000_pistol_glass_crack_decals.dds"]:
    for p in Path(r"./work/assets/textures").rglob(name):
        d=p.open("rb").read(148)
        fmt=struct.unpack_from("<I",d,128)[0]; h,w=struct.unpack_from("<II",d,12)
        mips=struct.unpack_from("<I",d,140)[0]
        print(name, "fmt",fmt,w,"x",h,"mips",mips,"bytes",p.stat().st_size)
        try:
            im=Image.open(p); im.load(); a=np.asarray(im.convert("RGB"),dtype=np.float32)
            print("  decoded", im.mode, "mean", a.reshape(-1,3).mean(0).round(1), "std", a.reshape(-1,3).std(0).round(1))
        except Exception as e: print("  decode fail:",e)
