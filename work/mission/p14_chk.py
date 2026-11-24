import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
recs=[]
for i in range(10416,11248,24):
    d=struct.unpack_from('<6I',b,i); recs.append((i,d[0],d[2],d[4]&0xffff,d[4]>>16))
for r in recs[:40]: print(hex(r[1]),r[2],'lo',hex(r[3]),'hi',hex(r[4]),'abs',hex(r[4]))
print()
def chk(off,base=0):
    t=base+off
    if t+24>len(b) or t<16: return 'OOB'
    d=struct.unpack_from('<6I',b,t)
    return 'h=%08x d1=%d d2=%d d3=%d'%(d[0],d[1],d[2],d[3])
for r in recs[:12]:
    print(hex(r[4]),'abs:',chk(r[4]),'| b11696:',chk(r[4],11696),'| b1960:',chk(r[4],1960))
