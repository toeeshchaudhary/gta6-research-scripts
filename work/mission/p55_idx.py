import json,os,sys,collections
sys.path.insert(0,r'.\work\mission')
import lib_min as L
OUT=r'.\work\mission\out'
src=L.build_dicts(); dic,origin=L.merged(src)
idx={}
cats=collections.Counter(); allkeys=collections.Counter()
for fn in os.listdir(OUT):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    d=json.load(open(os.path.join(OUT,fn),encoding='utf-8'))
    names=set(); nrec=0; nch=0
    for ch in d['chunks']:
        rs=ch.get('records')
        if not rs: continue
        nch+=1; nrec+=len(rs)
        for r in rs:
            k=int(r['key'],16)
            if k in dic: names.add(dic[k]); allkeys[dic[k]]+=1
    if names: idx[fn.replace('.json','.bin')]={'records':nrec,'rec_chunks':nch,'states':sorted(names)}
json.dump(idx, open(os.path.join(OUT,'_mission_index.json'),'w',encoding='utf-8'), indent=0)
print('files with >=1 resolved state:',len(idx))
top=sorted(idx.items(), key=lambda kv:-len(kv[1]['states']))[:10]
for f,v in top: print(f,v['records'],len(v['states']),v['states'][:8])
print()
print('distinct resolved key names:',len(allkeys))
STATE=set('INTRO Outro Leave Escape ATTACK ACCEPT Reject Surrender Taunt failed Chase Search Searching Regroup Confront Talk Interrogate Following Tracking Destroyed Saved Active Complete Completed Transition Challenge Aftermath Main CleanUp exit Reward Approach Enter Base Interact Scene encounter engaged Combat'.split())
for n,c in allkeys.most_common(40):
    print(' %-12s %5d %s'%(n,c,'STATE' if n in STATE else ''))
