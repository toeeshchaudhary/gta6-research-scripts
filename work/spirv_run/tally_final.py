import json,glob,collections,os
rows={}
for f in glob.glob('work/spirv_run/**/rows*.jsonl',recursive=True):
    for line in open(f,encoding='utf-8',errors='replace'):
        line=line.strip()
        if not line.startswith('{'): continue
        try: r=json.loads(line)
        except: continue
        n=r.get('name')
        if not n: continue
        p=rows.get(n)
        if p is None or (not p.get('val_ok') and r.get('val_ok')): rows[n]=r
by=collections.defaultdict(collections.Counter)
for r in rows.values():
    s=r.get('stage') or 'unset'
    by[s]['rows']+=1
    for k in ('spirv_ok','as_ok','val_ok'):
        if r.get(k): by[s][k]+=1
print("unique names with rows:",len(rows),"of 26503 corpus")
print("\nstage   rows   spirv_ok   as_ok  val_ok  pass%")
T=collections.Counter()
for s in sorted(by):
    c=by[s]; pct=100.0*c['val_ok']/c['rows'] if c['rows'] else 0
    print("%-7s %5d %8d %7d %7d %6.1f"%(s,c['rows'],c['spirv_ok'],c['as_ok'],c['val_ok'],pct))
    for k in c: T[k]+=c[k]
print("%-7s %5d %8d %7d %7d %6.1f"%('ALL',T['rows'],T['spirv_ok'],T['as_ok'],T['val_ok'],100.0*T['val_ok']/T['rows']))
errs=collections.Counter()
for r in rows.values():
    if not r.get('val_ok'):
        errs[(str(r.get('stage')),(r.get('error') or 'none')[:60])]+=1
print("\ntop failure causes:")
for (s,e),c in errs.most_common(10): print("  %5d  %-6s %s"%(c,s,e))
spv=set()
for d in ('work/spirv_run/spirv_s2','work/spirv_run/cs_spirv','work/spirv_run/gs_spirv','work/spirv_run/spirv_s2_unp'):
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if fn.endswith('.spv'): spv.add(fn[:-4])
print("\nunique .spv modules on disk:",len(spv))
print("names with a .spv but no row:",len(spv-set(rows)))
json.dump({'by_stage':{k:dict(v) for k,v in by.items()},'total':dict(T),
           'unique_rows':len(rows),'unique_spv':len(spv),
           'spv_without_row':len(spv-set(rows))},
          open('work/spirv_run/summary_final.json','w'),indent=1)
print("wrote summary_final.json")
