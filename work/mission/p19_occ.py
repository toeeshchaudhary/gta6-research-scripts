import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
import re
for v in [0xf48399a5,0x03d9a997,0x0bfc15e3]:
    raw=struct.pack('<I',v);h=[];i=b.find(raw)
    while i>=0 and len(h)<40: h.append(i);i=b.find(raw,i+1)
    print(hex(v),len(h),h[:25])
