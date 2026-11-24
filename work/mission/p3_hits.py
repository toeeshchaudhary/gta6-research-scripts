import struct,collections
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def hits(v):
    raw=struct.pack('<I',v); out=[];i=b.find(raw)
    while i>=0 and len(out)<40: out.append(i); i=b.find(raw,i+1)
    return out
for name,v in [('6081d83f',0x6081d83f),('d1c59792',0xd1c59792),('6a131547',0x6a131547),('807?553f',0x80553f47)]:
    h=hits(v); print(name,len(h),h[:20])
