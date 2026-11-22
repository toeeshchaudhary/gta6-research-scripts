import struct
def load(p):
    b=open(p,"rb").read(); nb=struct.unpack("<i",b[4:8])[0]; o=8; meta=[]
    for i in range(nb):
        pl=struct.unpack("<q",b[o:o+8])[0]; il=struct.unpack("<i",b[o+8:o+12])[0]; meta.append((pl,il)); o+=12
    p2=o; bl=[]
    for pl,il in meta: bl.append(b[p2:p2+il]); p2+=il
    return bl
def loose(b,o):
    if o+80>len(b): return False
    x,y,z=struct.unpack("<3f",b[o:o+12])
    for v in (x,y,z):
        if v!=v or abs(v)>30000: return False
    if x==0 and y==0 and z==0: return False
    if not(-6000<=z<=8000): return False
    if struct.unpack("<I",b[o+0x1C:o+0x20])[0]!=0: return False
    for k in range(4):
        if struct.unpack("<I",b[o+0x20+4*k:o+0x24+4*k])[0]<0x1000: return False
    return True
for f in ("109C363010","109BDDA010"):
    b=load("work\\xform\\out\\%s.bin"%f)[0]
    starts=[]; o=0
    while o+80<=len(b):
        if loose(b,o):
            c=1
            while loose(b,o+c*80): c+=1
            if c>=6: starts.append((o,c))
            o+=c*80
        else: o+=4
    print(f, "tables",len(starts),"records",sum(c for _,c in starts))
    print("  first:", [(hex(s),c) for s,c in starts[:8]])
