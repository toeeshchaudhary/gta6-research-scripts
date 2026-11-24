import struct, random
from pathlib import Path
from PIL import Image
import numpy as np
cands=[]
for p in Path(r"./work/assets/textures").rglob("*.dds"):
    d=p.open("rb").read(148)
    if len(d)<148: continue
    fmt=struct.unpack_from("<I",d,128)[0]
    h,w=struct.unpack_from("<II",d,12)
    if fmt in (98,77,71,99) and w>=1024 and h>=1024 and w==h:
        cands.append((p.stat().st_size,fmt,w,p))
random.seed(1); random.shuffle(cands)
print("square >=1024 candidates:",len(cands))
out=[]
for sz,fmt,w,p in cands[:60]:
    try:
        im=Image.open(p); im.load()
        a=np.asarray(im.convert("RGB").resize((256,256)),dtype=np.float32)
        std=a.reshape(-1,3).std(0).mean()
        mean=a.reshape(-1,3).mean(0)
        sat=float((a.max(2)-a.min(2)).mean())
        out.append((std,sat,mean,sz,fmt,w,p))
    except Exception as e:
        pass
out.sort(key=lambda r:-(r[0]))
for std,sat,mean,sz,fmt,w,p in out[:12]:
    print(f"std={std:5.1f} sat={sat:5.1f} mean={mean.round(0)} fmt={fmt} {w} {sz:8d} {p.name}")
