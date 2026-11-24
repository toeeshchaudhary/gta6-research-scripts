import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def show(s,e):
    for i in range(s,e,16):
        row=b[i:i+16]
        print('%6d %-47s |%s|'%(i,row.hex(' '),''.join(chr(c) if 32<=c<127 else '.' for c in row)))
show(392,700)
print('=====')
show(11264,11460)
