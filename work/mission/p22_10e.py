import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
base=38656
for k in range(7):
    o=base+119*k
    print('--- cell',k,'off',119*k)
    for i in range(o,o+119,16):
        print('   %6d %s'%(i,b[i:i+16].hex(' ')))
