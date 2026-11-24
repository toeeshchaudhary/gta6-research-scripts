import struct
def load(p):
    b=open(p,"rb").read(); nb=struct.unpack("<i",b[4:8])[0]; o=8; meta=[]
    for i in range(nb):
        pl=struct.unpack("<q",b[o:o+8])[0]; il=struct.unpack("<i",b[o+8:o+12])[0]; meta.append((pl,il)); o+=12
    p2=o; bl=[]
    for pl,il in meta: bl.append(b[p2:p2+il]); p2+=il
    return bl
b=load(r"work\xform\out\109C363010.bin")[0]
print("base   old-read (pos@record_base+0x00)      true read (pos@record_base+0x40)      yaw    archetype")
for i in range(8):
    base=0x50+i*80
    old=struct.unpack("<3f",b[base:base+12])
    true=struct.unpack("<3f",b[base+0x40:base+0x4C])
    yaw=struct.unpack("<f",b[base+0x4C:base+0x50])[0]
    h=struct.unpack("<I",b[base+0x6C:base+0x70])[0]
    print("0x%03X  (%12.4g,%12.4g,%12.4g)  (%9.3f,%9.3f,%9.3f)  %7.3f  0x%08X"%(base,*old,*true,yaw,h))
