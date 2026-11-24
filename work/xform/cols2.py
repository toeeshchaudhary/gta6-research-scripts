import struct, collections
def load(p):
    b=open(p,"rb").read(); nb=struct.unpack("<i",b[4:8])[0]; o=8; meta=[]
    for i in range(nb):
        pl=struct.unpack("<q",b[o:o+8])[0]; il=struct.unpack("<i",b[o+8:o+12])[0]; meta.append((pl,il)); o+=12
    p2=o; bl=[]
    for pl,il in meta: bl.append(b[p2:p2+il]); p2+=il
    return bl
b=load("work\\xform\\out\\109C363010.bin")[0]
o=0x90
recs=[]
for i in range(1130):
    r=o+i*80
    recs.append(struct.unpack("<20I", b[r:r+80]))
# check correlation of +0x20 floats with +0x00 floats
same=0
for d in recs:
    x0=struct.unpack("<f",struct.pack("<I",d[0]))[0]
    x5=struct.unpack("<f",struct.pack("<I",d[8]))[0]   # +0x20
    if abs(x0-x5)<1e-3: same+=1
print("records where float@+0x20 == float@+0x00:",same,"/",len(recs))
for k in (0,8,9,10,11):
    vals=[struct.unpack("<f",struct.pack("<I",d[k]))[0] for d in recs[:6]]
    print("col +0x%02X sample floats:"%(4*k), ["%.3f"%v for v in vals])
print()
print("distinct +0x2C:", collections.Counter(d[11] for d in recs).most_common(10))
print("distinct +0x28:", collections.Counter(d[10] for d in recs).most_common(5))
print("idx byte +0x1B samples:", [d[6]>>24 for d in recs[:8]], "max", max(d[6]>>24 for d in recs))
print("u16 +0x18:", collections.Counter(d[6]&0xFFFF for d in recs).most_common(4))
print("enum +0x10:", collections.Counter(d[4] for d in recs).most_common(4))
print("+0x3C..", collections.Counter(d[15] for d in recs).most_common(6))
