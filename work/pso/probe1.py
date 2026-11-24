import sys,struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
print("files",len(files))
ok=0; shapes=collections.Counter(); bad=[]
for f in files[:400]:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': continue
    ln=struct.unpack('>I',d[4:8])[0]
    pl=d[8:ln]
    root,count=struct.unpack('<II',pl[:8])
    entries=[]
    off=8; good=True
    for i in range(count):
        if off+16>len(pl): good=False;break
        filler=pl[off:off+8]; h,el=struct.unpack('<II',pl[off+8:off+16])
        entries.append((filler.hex(),h,el)); off+=16
    if not good: shapes['count_overflow']+=1; bad.append((f,root,count,len(pl))); continue
    term=pl[off:off+16]; off+=16
    data=pl[off:]
    shapes[('filler_aaaa' if all(e[0]=='a'*16 for e in entries) else 'filler_other',
            term.hex()=='a'*16+'70'*8, sum(e[2] for e in entries), len(data))]+=1
    if sum(e[2] for e in entries)<=len(data): ok+=1
print("ok(sum lens <= data)",ok,"of",len(files[:400]))
for k,v in shapes.most_common(12): print(v,k)
print("bad sample",bad[:5])
