import struct,collections
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read();n=len(b)
def ok(i):
    if i+32>n: return False
    d=struct.unpack_from('<8I',b,i)
    return d[0]>0 and d[1]==0 and d[3]==0 and d[5]==0 and d[7]==0
pos=[i for i in range(n-32) if ok(i)]
print('n',len(pos))
print([x for x in pos if 11200<x<11500])
# greedy chain with stride 32
inchain=set()
chains=[]
for i in pos:
    if i in inchain: continue
    c=[i];cur=i
    while cur+32 in set(pos):
        cur+=32;c.append(cur)
    if len(c)>=3:
        chains.append(c);inchain.update(c)
print('chains',len(chains),'records',sum(len(c) for c in chains))
for c in chains: print(len(c),c[0],c[-1])
