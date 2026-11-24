import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
print('0x108 @10408 len840:')
print(b[10408:10408+96].hex(' '))
print()
for i in range(11264,11520,32):
    d=struct.unpack_from('<8I',b,i)
    off=d[4]>>16; cnt=d[4]&0xffff; st=p
    print('key=%08x d2=%d band=%d off=%d stride=%d'%(d[0],d[2],cnt,off,d[6]&0xffff),end=' ')
    base=10408
    print('->',[hex(x) for x in struct.unpack_from('<8I',b,base+off*4)])
