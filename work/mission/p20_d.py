import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def show(s,e):
    for i in range(s,e,16): print('%6d %s'%(i,b[i:i+16].hex(' ')))
show(34460,34550)
print('--- 34000 region, 4-dword aligned rows')
for i in range(34000,34064,16):
    print('%6d %s'%(i,b[i:i+16].hex(' ')))
