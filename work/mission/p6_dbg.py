import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
for i in [11328,11360,11392,11424,11456]:
    print(i,[hex(x) for x in struct.unpack_from('<8I',b,i)])
