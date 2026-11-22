import sys,os,time
sys.path.insert(0,r'.\work\mission')
import lib_min as L
files=sorted(f for f in os.listdir(L.GROUPS) if f.endswith('.bin'))
for fn in files[20:40]:
    b=open(os.path.join(L.GROUPS,fn),'rb').read()
    c=L.parse_container(b)
    if c is None:
        print(fn,len(b),'NOT PSIN',b[:4]); continue
    big=[(hex(ch['tag']),ch['size']) for ch in c['chunks'] if L.is_index(ch['tag']) and ch['size']>200000]
    print(fn,len(b),'chunks',len(c['chunks']),'bigidx',big[:3])
