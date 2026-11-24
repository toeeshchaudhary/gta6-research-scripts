import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def recs(off,size):
    out=[]
    for i in range(off,off+size,32):
        d=struct.unpack_from('<8I',b,i); out.append(d)
    return out
print('chunk 0x10d @38032')
for r in recs(38032,224): print(hex(r[0]),r[2],hex(r[4]),hex(r[6]),'off=',r[4]&0xffff,'n=',r[6]&0xffff)
print()
print('0x10c data @34000 first 160 bytes:')
print(b[34000:34160].hex(' '))
print()
for r in recs(38032,224):
    o=34000+(r[4]&0xffff); n=r[6]&0xffff
    print(hex(r[0]),o,n,[hex(x) for x in struct.unpack_from('<%dI'%n,b,o)])
