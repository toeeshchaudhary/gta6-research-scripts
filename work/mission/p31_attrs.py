import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
for v in [0xfbc129d2,0x691362f2,0xdd245b9c,0x8da61c38,0x0c928991]:
    raw=struct.pack('<I',v);h=[];i=b.find(raw)
    while i>=0 and len(h)<10: h.append(i);i=b.find(raw,i+1)
    print('%08x'%v,h)
