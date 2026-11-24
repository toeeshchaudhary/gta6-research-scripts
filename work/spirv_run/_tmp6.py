import glob,json,os,collections,hashlib
def h(p): return hashlib.md5(open(p,'rb').read()).hexdigest()
idx=json.load(open(r's2_in\index.json',encoding='utf-8'))
stage={os.path.splitext(e['file'])[0]:e['stage'] for e in idx}
hs={}
for d in [r's2_in\disasm',r'cs_in\disasm',r'spirv_in\disasm']:
    for f in os.listdir(d):
        if f.endswith('.s'):
            n=f[:-2]; hs.setdefault(n,set()).add(h(os.path.join(d,f)))
allh={(stage.get(n,'?'),x) for n in hs for x in hs[n]}
print('distinct program hashes by stage',dict(collections.Counter(s for s,_ in allh)))
rows={}
for p in sorted(glob.glob(r'logs*\*rows*.jsonl'),key=os.path.getmtime):
    for l in open(p,encoding='utf-8'):
        if l.strip():
            r=json.loads(l)
            for x in hs.get(r['name'],[]):
                rows[(stage.get(r['name'],'?'),x)]=r
print('resolved programs',len(rows),dict(collections.Counter(k[0] for k in rows)))
missing=allh-set(rows)
print('no row',len(missing),dict(collections.Counter(s for s,_ in missing)))
ok=sum(1 for k,r in rows.items() if r['val_ok'])
print('validated',ok,f'{100*ok/len(rows):.2f}% of resolved')
