import json, collections
idx = collections.defaultdict(list)
n=0
for line in open(r'work/arch/dict/resnames_full.tsv', encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    parts=line.rstrip('\n').split('\t')
    if len(parts)<4: continue
    res,name,h,kind=parts[:4]
    idx[h.lower()].append((res,name,kind)); n+=1
print('indexed',n,'distinct hashes',len(idx))
s=json.load(open(r'work/world/scene_streets.json'))
cnt=collections.Counter(i['hash'].lower() for i in s['instances'])
print('street hashes',len(cnt),'instances',sum(cnt.values()))
hit=[h for h in cnt if h in idx]
print('bound hashes',len(hit), 'instances', sum(cnt[h] for h in hit))
for h in ['0x2f7e64d1','0xd3e22d9a']:
    print(h, cnt.get(h), idx.get(h))
print('top:')
for h,c in cnt.most_common(12):
    print(h,c,idx.get(h))
