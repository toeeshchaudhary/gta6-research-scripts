import glob,os,re,struct,collections
# collect shader tokens
toks=set(); names=set()
for d in ('spirv','spirv_s2','spirv_s2_unp'):
    for f in glob.glob(os.path.join('work\\spirv_run',d,'*.spv')):
        b=os.path.basename(f)
        m=re.match(r'^(\d+)_([a-z]+)_(.*)_([0-9a-f]{8})_Wrapped\.spv$',b)
        if m:
            toks.add(int(m.group(4),16)); names.add(m.group(3))
print("tokens",len(toks),"names",len(names))
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
hit=0; tot=0; hitfiles=0; matched=collections.Counter()
for f in files:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': continue
    tot+=1; fh=False
    for o in range(0,len(d)-4,1):
        v=struct.unpack('<I',d[o:o+4])[0]
        if v in toks: matched[v]+=1; fh=True
    if fh: hitfiles+=1
print("files",tot,"files with any shader-token match",hitfiles,"distinct tokens matched",len(matched),"total matches",sum(matched.values()))
print(matched.most_common(5))
