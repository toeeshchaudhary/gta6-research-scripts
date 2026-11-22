import sys,os,time,json
sys.path.insert(0,r'.\work\mission')
import lib_min as L
files=sorted(f for f in os.listdir(L.GROUPS) if f.endswith('.bin'))
for fn in files[24:28]:
    b=open(os.path.join(L.GROUPS,fn),'rb').read()
    t=time.time(); c=L.parse_container(b); t1=time.time()
    n=0
    for ch in c['chunks']:
        if L.is_index(ch['tag']): n+=len(L.parse_records(b,ch['off'],ch['size']))
    print(fn,len(b),'chunks',len(c['chunks']),'idx',n,'parse %.3fs'%(t1-t),'recs %.3fs'%(time.time()-t1))
