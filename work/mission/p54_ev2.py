import json,os,sys,collections
sys.path.insert(0,r'.\work\mission')
import lib_min as L
OUT=r'.\work\mission\out'
tot=0; inb=0; valsum=0; chunks=0; asc=0; asc_tot=0; poolchunks=0
for fn in os.listdir(OUT):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    d=json.load(open(os.path.join(OUT,fn),encoding='utf-8'))
    for ch in d['chunks']:
        rs=ch.get('records')
        if not rs: continue
        chunks+=1
        prev=-1; ok=True
        for r in rs:
            tot+=1
            if 'values' in r: inb+=1; valsum+=len(r['values'])
            if r['offset']<prev: ok=False
            prev=r['offset']
        if len(rs)>2:
            asc_tot+=1; asc+= 1 if ok else 0
print('chunks',chunks,'recs',tot,'decoded',inb,'(%.2f%%)'%(100*inb/max(1,tot)),'dwords',valsum)
print('monotone chunks %.1f%% (%d/%d)'%(100*asc/max(1,asc_tot),asc,asc_tot))
d=json.load(open(os.path.join(OUT,'g1730_045AE000.json')))
for ch in d['chunks']:
    if ch['role']=='records': print('REC CHUNK',ch['tag'],ch['size'],ch['validity'],len(ch['records']))
r=[x for x in d['chunks'] if x['tag']=='00000109'][0]['records']
for x in r:
    if x['key']=='6a131547': print(json.dumps(x))
