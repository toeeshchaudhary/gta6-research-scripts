import glob,os,re,struct,collections,zlib
toks=set()
for d in ('spirv','spirv_s2','spirv_s2_unp'):
    for f in glob.glob(os.path.join('work\\spirv_run',d,'*.spv')):
        m=re.search(r'_([0-9a-f]{8})_Wrapped\.spv$',os.path.basename(f))
        if m: toks.add(int(m.group(1),16))
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
# u64 variants
pats={'le64_low':lambda t: struct.pack('<Q',t),'le64_hi':lambda t: struct.pack('<Q',t<<32),'be64_hi':lambda t: struct.pack('>Q',t<<32)}
cnt=collections.Counter(); fh=collections.Counter(); tot=0
for f in files:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': continue
    tot+=1
    for k,fn in pats.items():
        found=0
        for t in toks:
            if fn(t) in d: found+=1
        if found: cnt[k]+=found; fh[k]+=1
print("files",tot)
for k in pats: print(k,"distinct tokens found",cnt[k],"files with >=1",fh[k])
# LSNS decompression attempts
okc=collections.Counter()
for f in files[:200]:
    d=open(f,'rb').read(); i=d.find(b'LSNS')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; pl=d[i+8:i+ln]
    for name,w in (('zlib',15),('raw',-15),('gzip',31)):
        try:
            o=zlib.decompressobj(w).decompress(pl); okc[name]+=1
        except Exception: okc[name+'_fail']+=1
print(okc)
