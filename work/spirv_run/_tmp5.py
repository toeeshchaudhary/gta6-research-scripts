import glob,json,os,collections,hashlib
def h(p):
    return hashlib.md5(open(p,'rb').read()).hexdigest()
idx=json.load(open(r's2_in\index.json',encoding='utf-8'))
stage={os.path.splitext(e['file'])[0]:e['stage'] for e in idx}
# hashes of available .s in both dirs
hs={}
for d in [r's2_in\disasm',r'cs_in\disasm']:
    for f in os.listdir(d):
        if f.endswith('.s'):
            p=os.path.join(d,f); n=f[:-2]
            hs.setdefault(n,set()).add(h(p))
allh=set()
for n in hs:
    for x in hs[n]: allh.add((stage.get(n,'?'),x))
print('distinct program hashes by stage',collections.Counter(s for s,_ in allh))
print('s2 entries',len(stage))
# rows: resolve to hash
rows={}
for p in sorted(glob.glob(r'logs*\*rows*.jsonl'),key=os.path.getmtime):
    for l in open(p,encoding='utf-8'):
        if l.strip():
            r=json.loads(l)
            for x in hs.get(r['name'],[]):
                rows[(stage.get(r['name'],'?'),x)]=r
print('row-equivalent distinct programs',len(rows))
print(collections.Counter(k[0] for k in rows))
missing=allh-set(rows)
print('distinct programs with no row',len(missing),collections.Counter(s for s,_ in missing))
