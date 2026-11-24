import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
desc=[];i=8
while i<392:
    t,s=struct.unpack_from('<II',b,i); desc.append((t,s)); i+=16
offs=[];cur=392
for t,s in desc: offs.append((t,cur,s)); cur+=s
print('chunks:')
for t,o,s in offs: print(' %04x @%d len %d'%(t,o,s))
print()
def parse(o,s):
    out=[]
    for i in range(o,o+s,32):
        d=struct.unpack_from('<8I',b,i)
        out.append(d)
    return out
for (t,o,s),(t2,o2,s2) in zip(offs[6:13],offs[7:14]):
    print('table %04x @%d len%d -> next %04x @%d len%d'%(t,o,s,t2,o2,s2))
    for d in parse(o,s):
        hi=d[4]>>16; lo=d[4]&0xffff
        print('   key %08x c=%d lo=%d off=%d pair=%d'%(d[0],d[2],lo,hi,d[6]&0xffff), end='')
        tgt=o2+hi
        print(' tgt=%d'%tgt, end='')
        if tgt+16<=o2+s2: print(' OK %s'%b[tgt:tgt+16].hex(' '))
        else: print(' OOB')
    print()
