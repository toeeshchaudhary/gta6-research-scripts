import struct,sys
def joaat(s):
    h=0
    for c in s.lower().encode('latin-1','replace'):
        h=(h+c)&0xFFFFFFFF; h=(h+(h<<10))&0xFFFFFFFF; h^=h>>6
    h=(h+(h<<3))&0xFFFFFFFF; h^=h>>11
    return (h+(h<<15))&0xFFFFFFFF
d={}
voc=[l.split('\t') for l in open(r'.\work\story\s17_repeated_keys.txt',encoding='utf-8',errors='replace').read().splitlines() if l.strip()]
for parts in voc:
    h=int(parts[0],16); name=parts[2] if len(parts)>2 else ''
    d.setdefault(h,name)
for s in open(r'.\work\story\missions_common_rpf.txt',encoding='utf-8').read().split():
    d.setdefault(joaat(s),'MISSION:'+s)
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
# all dword positions of 32-byte stride records in tables
offs=[(11248,448),(1960,8448),(10408,840),(11696,22080)]
seen={}
for off,size in offs:
    for i in range(off,off+size,32):
        v=struct.unpack_from('<I',b,i)[0]
        seen[v]=seen.get(v,0)+1
res=sorted(seen.items(), key=lambda kv:-kv[1])
print('distinct dword-0 values in table chunks:',len(seen),'of which resolve:',sum(1 for k,_ in res if k in d))
for k,c in res[:40]:
    print('%08x x%-4d %s'%(k,c,d.get(k,'')))
