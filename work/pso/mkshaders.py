import glob,os,re
seen={}
for d in ('spirv','spirv_s2','spirv_s2_unp'):
    for f in glob.glob(os.path.join('work\\spirv_run',d,'*.spv')):
        m=re.match(r'^\d+_([a-z]+)_(.*)_([0-9a-f]{8})_Wrapped\.spv$',os.path.basename(f))
        if m: seen.setdefault(m.group(3),(m.group(2),m.group(1)))
with open(r'work\pso\shader_index.txt','w',encoding='ascii') as w:
    for h,(n,s) in seen.items(): w.write("%s %s/%s\n"%(h,s,n))
print(len(seen))
