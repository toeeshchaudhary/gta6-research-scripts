import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def recs(off,size,skip=16):
    out=[]
    for i in range(off+skip,off+size-15,32):
        d=struct.unpack_from('<8I',b,i)
        out.append(d)
    return out
for name,off,size in [('0109',11248,448),('010d',38032,224),('010f',51984,224),('0111',53552,224),('0113',84688,224)]:
    print(name, [ (hex(d[0]), d[2], hex(d[4]), d[6]&0xffff) for d in recs(off,size)])
