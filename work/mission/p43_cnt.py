import sys,os,struct,time
sys.path.insert(0,r'.\work\mission')
import lib_min as L
files=sorted(f for f in os.listdir(L.GROUPS) if f.endswith('.bin'))
mx=[]
for fn in files[:60]:
    b=open(os.path.join(L.GROUPS,fn),'rb').read()
    c=L.parse_container(b)
    if not c: continue
    for ch in c['chunks']:
        if L.is_index(ch['tag']):
            for r in L.parse_records(b,ch['off'],ch['size']):
                mx.append((r['count'],fn,hex(ch['tag']),hex(r['key'])))
mx.sort(reverse=True)
print('max counts:',mx[:8])
print('n records',len(mx))
