import struct, re
from pathlib import Path
rows=[]
for p in Path(r"./work/assets/textures").rglob("*.dds"):
    n=p.stem
    if re.search(r"texture_\d+", n) or n.startswith("texture"): continue
    d=p.open("rb").read(148)
    fmt=struct.unpack_from("<I",d,128)[0]
    h,w=struct.unpack_from("<II",d,12)
    rows.append((fmt,w,h,p.stat().st_size,n))
print("named count:",len(rows))
import collections
print(collections.Counter(r[0] for r in rows).most_common())
kw=["camo","wood","metal","leather","fabric","dirt","grass","rock","brick","asphalt","concrete","tile","wall","paint","rust","skin","face","clothes","shirt","gun","wpn","car","vehicle","wheel","tire","logo"]
for k in kw:
    hits=[r for r in rows if k in r[4].lower()]
    if hits:
        print("==",k,len(hits))
        for r in hits[:8]: print(f"   {r[0]:3d} {r[1]}x{r[2]} {r[3]:9d} {r[4]}")
