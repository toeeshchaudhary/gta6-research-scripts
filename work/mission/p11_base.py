import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def show(s,e,label):
    print('---',label,s)
    for i in range(s,e,16): print('%6d %s'%(i,b[i:i+16].hex(' ')))
for base,off in [(392,15360),(10408,5120),(11696,0),(19696,0)]:
    t=base+off
    show(t-8,t+56,'base%d off%d'%(base,off))
