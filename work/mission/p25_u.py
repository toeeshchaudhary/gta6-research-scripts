import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
print('0x110 as dword-offsets from 52224:')
for k in range(6):
    o=52224+12*4*k
    print(' k',k,o,b[o:o+48].hex(' '))
print()
print('0x112 head 160:')
for i in range(53776,53936,16): print('  %6d %s'%(i,b[i:i+16].hex(' ')))
