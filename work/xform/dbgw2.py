import struct
b=open(r"work\xform\out\109C363010.bin","rb").read()
nb=struct.unpack("<i",b[4:8])[0]; o=8; meta=[]
for i in range(nb):
    pl=struct.unpack("<q",b[o:o+8])[0]; il=struct.unpack("<i",b[o+8:o+12])[0]; meta.append((pl,il)); o+=12
p=o; blocks=[]
for pl,il in meta: blocks.append(b[p:p+il]); p+=il
b0=blocks[0]
for o in (0x90,0xE0,0x130,0x180):
    print(hex(o), struct.unpack("<3f",b0[o:o+12]), "u10",struct.unpack("<I",b0[o+0x10:o+0x14])[0],
          "u14",struct.unpack("<I",b0[o+0x14:o+0x18])[0],
          "u16_18",struct.unpack("<H",b0[o+0x18:o+0x1A])[0],
          "idx",struct.unpack("<H",b0[o+0x1A:o+0x1C])[0],
          "u2C",hex(struct.unpack("<I",b0[o+0x2C:o+0x30])[0]),
          "u30",hex(struct.unpack("<I",b0[o+0x30:o+0x34])[0]))
