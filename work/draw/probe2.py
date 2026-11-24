import json, collections
names = {}
for f in [r'work/arch/dict/resnames_full.tsv', r'work/arch/dict/resnames_packs.tsv']:
    for line in open(f, encoding='utf-8', errors='replace'):
        if line.startswith('#'): continue
        p=line.rstrip('\n').split('\t')
        if len(p)<4: continue
        names.setdefault(p[2].lower(), []).append((p[0],p[1],p[3],f.split('\\')[-1]))
print('resname hashes', len(names))
def joaat(s):
    h=0
    for c in s.lower():
        h=(h+ord(c))&0xffffffff
        h=(h+(h<<10))&0xffffffff
        h^=h>>6
    h=(h+(h<<3))&0xffffffff
    h^=h>>11
    h=(h+(h<<15))&0xffffffff
    return h
s=json.load(open(r'work/world/scene_streets.json'))
cnt=collections.Counter(i['hash'].lower() for i in s['instances'])
res=json.load(open(r'work/arch/out/scene_streets_resolved.json'))
named={i['hash']:i.get('archetype') for i in res['instances'] if i.get('archetype')}
print('named hashes',len(named))
hit=0
for h in sorted(cnt, key=lambda h:-cnt[h]):
    if h in names: print('BOUND',h,cnt[h],names[h][:1])
for n in ['forklift','bulldozer','bison900','bison','rebel','ambulance','coach','futo']:
    print(n, hex(joaat(n)), [k for k,v in names.items() if any(x[1].lower()==n for x in v)][:3])
