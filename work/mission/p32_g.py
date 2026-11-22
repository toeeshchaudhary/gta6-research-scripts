p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
for i in range(2384,2720,16): print('%6d %s'%(i,b[i:i+16].hex(' ')))
