import glob,json,os,random
# (1) archived unpatched failures with the artefact error
art=[json.loads(l)['name'] for l in open(r'logs_fin\rows.part5_unpatched.jsonl',encoding='utf-8')
     if l.strip() and 'normalized encoding' in (json.loads(l)['error'] or '')]
# (2) residual "normalized encoding" rows under the patched translator
res=[]
for p in sorted(glob.glob(r'logs*\*rows*.jsonl'),key=os.path.getmtime):
    for l in open(p,encoding='utf-8'):
        if l.strip():
            r=json.loads(l)
            if 'normalized encoding' in (r['error'] or ''): res.append(r['name'])
res=sorted(set(res))
random.seed(7); sample=random.sample(res,40)
names=sorted(set(art)|set(sample))
open('delta_names.txt','w').write('\n'.join(names))
print('artefact-class names',len(art),'residual pool',len(res),'sampled',len(sample),'total',len(names))
