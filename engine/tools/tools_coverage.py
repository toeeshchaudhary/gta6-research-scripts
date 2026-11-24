import struct
from pathlib import Path
from collections import Counter
supported={71,72,77,78,80,83,95,98,99,28,29,87,91,10,2}
c=Counter(); bad=Counter(); n=0
for p in Path("./work/assets").rglob("*.dds"):
    d=p.open("rb").read(148); n+=1
    fmt=struct.unpack_from("<I",d,128)[0]
    (c if fmt in supported else bad)[fmt]+=1
print("total",n,"supported",sum(c.values()),f"{100*sum(c.values())/n:.2f}%","unsupported",sum(bad.values()),f"{100*sum(bad.values())/n:.2f}%")
print("supported by dxgi:",dict(sorted(c.items())))
print("unsupported by dxgi:",dict(sorted(bad.items())))
