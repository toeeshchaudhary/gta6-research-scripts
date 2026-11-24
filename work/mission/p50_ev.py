import json,os,sys,collections
sys.path.insert(0,r'.\work\mission')
import lib_min as L
OUT=r'.\work\mission\out'
tot=0; inb=0; asc=0; asc_tot=0; chunks=0
valsum=0
for fn in os.listdir(OUT):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    d=json.load(open(os.path.join(OUT,fn),encoding='utf-8'))
    L_=d['len']
    for ch in d['chunks']:
        rs=ch.get('records')
        if not rs: continue
        chunks+=1
        prev=-1; ok=True
        for r in rs:
            tot+=1
            tgt=ch['off']+r['offset']
            if 'values' in r:
                inb+=1; valsum+=len(r['values'])
            if r['offset']>=prev: pass
            else: ok=False
            prev=r['offset']
        if len(rs)>2:
            asc_tot+=1
            if ok: asc+=1
print('record chunks',chunks,'records',tot)
print('records with decoded values',inb,'(%.2f%%)'%(100*inb/max(1,tot)),'total dwords',valsum)
print('chunks with monotone ascending offsets',asc,'/',asc_tot,'(%.1f%%)'%(100*asc/max(1,asc_tot)))
