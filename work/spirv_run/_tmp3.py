import glob,json,os,re,collections
def key(n): return re.sub(r'^\d+_','',n)
idx=json.load(open(r's2_in\index.json',encoding='utf-8'))
stage={key(os.path.splitext(e['file'])[0]):e['stage'] for e in idx}
print('corpus keys',len(stage))
rows={}; src={}
for p in sorted(glob.glob(r'logs*\*rows*.jsonl'),key=os.path.getmtime):
    for l in open(p,encoding='utf-8'):
        if l.strip():
            r=json.loads(l); k=key(r['name']); rows[k]=r; src[k]=p
print('row keys',len(rows),'in corpus',len(set(rows)&set(stage)))
c=collections.Counter()
for k,r in rows.items():
    c[(stage.get(k,'OUT'),bool(r['val_ok']))]+=1
print(sorted(c.items(),key=lambda x:-x[1])[:12])
dis=set()
for d in [r's2_in\disasm',r'cs_in\disasm']:
    dis|={key(os.path.splitext(f)[0]) for f in os.listdir(d) if f.endswith('.s')}
print('dis keys',len(dis),'corpus with .s',len(dis&set(stage)))
print('corpus with s, no row', len([k for k in stage if k in dis and k not in rows]))
print(collections.Counter(stage[k] for k in stage if k in dis and k not in rows))
