import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
for i in range(8,392,16):
    t,s=struct.unpack_from('<II',b,i)
    print(i,hex(t),s,b[i+8:i+16].hex())
print('---384..520---')
print(b[384:520].hex(' '))
