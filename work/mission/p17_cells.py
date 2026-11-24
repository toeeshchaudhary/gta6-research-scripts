import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
for i in range(11696,11696+400,20):
    d=struct.unpack_from('<5I',b,i)
    f=struct.unpack_from('<5f',b,i)
    print('%6d off=%3d'%(i,i-11696),' '.join('%08x'%x for x in d),'|',' '.join('%.4g'%x for x in f))
