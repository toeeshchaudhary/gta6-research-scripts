import json,os,collections
OUT=r'.\work\mission\out'
bands=collections.Counter(); nrec=[]; sizes=[]
nonpsin=0; total=0
for fn in os.listdir(r'.\work\scripts\out\story_groups'):
    if fn.endswith('.bin'): total+=1
for fn in os.listdir(OUT):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    d=json.load(open(os.path.join(OUT,fn),encoding='utf-8'))
    sizes.append(d['len'])
    n=sum(len(c.get('records',[])) for c in d['chunks'])
    nrec.append(n)
    b = 0 if n==0 else 1 if n<10 else 2 if n<50 else 3 if n<200 else 4
    bands[b]+=1
print('total bins',total,'parsed',len(nrec),'non-psin',total-len(nrec))
print('record bands 0/[1-9]/[10-49]/[50-199]/200+ :',dict(bands))
sizes.sort(); nrec.sort()
print('size p50',sizes[len(sizes)//2],'max',sizes[-1])
print('records p50',nrec[len(nrec)//2],'max',nrec[-1],'sum',sum(nrec))
