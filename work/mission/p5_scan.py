import struct,collections
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
n=len(b)
def ok(i):
    if i+32>n: return False
    d=struct.unpack_from('<8I',b,i)
    return d[1]==0 and d[3]==0 and d[5]==0 and d[7]==0 and d[0]>0
# find all valid-template positions
pos=[i for i in range(0,n-32) if ok(i)]
print('valid template positions:',len(pos))
# cluster into chains with stride 32
chains=[];cur=[pos[0]] if pos else []
for a,bb in zip(pos,pos[1:]):
    if bb-a==16 or bb-a==32: cur.append(bb)
    else:
        chains.append(cur);cur=[bb]
if cur: chains.append(cur)
chains=[c for c in chains if len(c)>=3]
print('chains len>=3:',len(chains))
for c in chains[:10]: print(len(c),c[0],'..',c[-1])
print('total positions in chains>=3:',sum(len(c) for c in chains))
# stride distribution inside chains
st=collections.Counter()
for c in chains:
    for a,bb in zip(c,c[1:]): st[bb-a]+=1
print('stride dist',st)
