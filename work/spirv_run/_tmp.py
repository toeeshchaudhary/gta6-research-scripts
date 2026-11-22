import glob,json,os,collections
idx=json.load(open(r's2_in\index.json',encoding='utf-8'))
stage={os.path.splitext(e['file'])[0]:[e['stage']] for e in idx}
rows={}; src={}
for p in sorted(glob.glob(r'logs*\*rows*.jsonl'),key=os.path.getmtime):
    for l in open(p,encoding='utf-8'):
        if l.strip():
            r=json.loads(l); rows[r['name']]=r; src[r['name']]=os.path.basename(os.path.dirname(p))
out=[n for n in rows if n not in stage]
print('out-of-corpus rows',len(out))
print(collections.Counter(rows[n]['stage'] for n in out))
print(collections.Counter(src[n] for n in out))
print(out[:5])
