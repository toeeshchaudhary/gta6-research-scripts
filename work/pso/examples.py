import json,collections
rows=[]
aggr=collections.Counter()
for line in open('work/pso/dump/script.jsonl',encoding='utf-8'):
    j=json.loads(line); p=j['Pipeline']; cl=j['Classification']
    hb=[b for b in j['Blocks'] if b['StructHash']==0xAEB623D8]
    nh=sum(len(it) for b in hb for it in b['Items'])
    aggr['filesWithHashBlock'] += 1 if hb else 0
    aggr['matches'] += int(p.get('hashMatchesShaderToken',0) or 0)
    rows.append((j['Source'].split('\\')[-1], p.get('stateMask0'), p.get('stateMask1'), p.get('stateMask2'), p.get('stateByte0'), cl.get('drawType'), nh, p.get('hashMatchesShaderToken')))
print("files with hash block:",aggr['filesWithHashBlock'],"total shader-token matches:",aggr['matches'],"of",len(rows),"files")
rows.sort(key=lambda r:(r[6] or 0), reverse=True)
print("\n-*- examples (file, mask0, mask1, mask2, byte0, drawType, nHashes, shaderMatches)")
for r in rows[:12]: print(r)
print("\n-*- mask0 histogram (all)")
c=collections.Counter(r[1] for r in rows); print(c.most_common(15))
print("\n-*- byte0 histogram"); print(collections.Counter(r[4] for r in rows).most_common(10))
