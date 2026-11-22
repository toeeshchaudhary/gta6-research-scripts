import struct, os
from pathlib import Path
from PIL import Image
cands=[]
for p in Path(r"./work/assets/textures").rglob("*.dds"):
    d=p.open("rb").read(148)
    if len(d)<148 or d[:4]!=b"DDS ": continue
    fmt=struct.unpack_from("<I",d,128)[0] if d[84:88]==b"DX10" else None
    h,w=struct.unpack_from("<II",d,12)
    if fmt in (71,72,77,78) and w>=512 and w==h and p.stat().st_size<6_000_000:
        cands.append((p.stat().st_size,fmt,w,p))
print(len(cands),"candidates")
os.makedirs("./engine/_texprev", exist_ok=True)
ok=0
for i,(sz,fmt,w,p) in enumerate(sorted(cands)[:24]):
    try:
        im=Image.open(p); im.load()
        im=im.convert("RGB"); im.thumbnail((256,256))
        im.save(f"./engine/_texprev/{i:02d}_f{fmt}_{w}_{p.stem[:40]}.png")
        ok+=1
    except Exception as e:
        print("fail",p.name,e)
print("converted",ok)
