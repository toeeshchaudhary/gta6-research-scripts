import struct
b=open(r"work\xform\out\109C363010.bin","rb").read()
nb=struct.unpack("<i",b[4:8])[0]; o=8; meta=[]
for i in range(nb):
    pl=struct.unpack("<q",b[o:o+8])[0]; il=struct.unpack("<i",b[o+8:o+12])[0]; meta.append((pl,il)); o+=12
p=o; blocks=[]
for pl,il in meta: blocks.append(b[p:p+il]); p+=il
b0=blocks[0]
print("len",len(b0))
o=0x90
print("pos", struct.unpack("<3f",b0[o:o+12]))
print("f0C", struct.unpack("<f",b0[o+0x0C:o+0x10]))
print("u10",struct.unpack("<I",b0[o+0x10:o+0x14])[0],"u14",struct.unpack("<I",b0[o+0x14:o+0x18])[0])
print("u16@18",struct.unpack("<H",b0[o+0x18:o+0x1A])[0],"u16@1A",struct.unpack("<H",b0[o+0x1A:o+0x1C])[0])
print("u2C",hex(struct.unpack("<I",b0[o+0x2C:o+0x30])[0]))
# count how many consecutive pass
def ok(o):
    if o+64>len(b0): return False
    x,y,z=struct.unpack("<3f",b0[o:o+12])
    if not all(map(lambda v: v==v and abs(v)<=30000, (x,y,z))): return False
    if x==0.0 and y==0.0 and z==0.0: return False
    if z<-6000 or z>8000: return False
    if struct.unpack("<I",b0[o+0x10:o+0x14])[0]!=2: return False
    if struct.unpack("<I",b0[o+0x14:o+0x18])[0]!=2: return False
    if struct.unpack("<H",b0[o+0x18:o+0x1A])[0]!=2: return False
    if struct.unpack("<I",b0[o+0x2C:o+0x30])[0]<0x1000: return False
    return True
print("ok(0x90)",ok(0x90))
c=0
while ok(0x90+c*64): c+=1
print("chain",c)
