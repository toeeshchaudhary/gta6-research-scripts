p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
for off in (51984,53552,84688,38032):
    print('---',off, b[off:off+32].hex(' '))
import struct
for off in (51984,53552,84688):
    print(off,[ (hex(struct.unpack_from('<8I',b,off+32*i)[0]), hex(struct.unpack_from('<8I',b,off+32*i)[4])) for i in range(7)])
