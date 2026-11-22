p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def show(s,e):
    for i in range(s,e,16):
        q=b[i:i+16]
        fl=[]
        for j in range(0,16,4):
            import struct
            v=struct.unpack_from('<f',q,j)[0]
            fl.append('%.3g'%v)
        print('%6d %-47s %s'%(i,q.hex(' '),' '.join(fl)))
show(11696,11860)
print('=== 0x10a tail')
show(33680,33780)
