import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
stats=collections.Counter(); bad=[]
al=lambda n:(n+15)//16*16
for f in files:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': stats['nomagic']+=1; continue
    ln=struct.unpack('>I',d[4:8])[0]
    if ln>len(d): stats['trunc']+=1; continue
    pl=d[8:ln]
    if len(pl)<8: stats['tiny']+=1; continue
    f8,tail=struct.unpack('<II',pl[:8]); o=8; ents=[]
    while o+16<=len(pl):
        fl=pl[o:o+8]; h,l=struct.unpack('<II',pl[o+8:o+16]); ents.append((fl.hex(),h,l)); o+=16
        if h==0x70707070: break
    if not ents or ents[-1][1]!=0x70707070: stats['noterm']+=1; bad.append(f); continue
    if any(e[0]!='a'*16 for e in ents[:-1]): stats['badfill']+=1; bad.append(f); continue
    tot=sum(al(e[2]) for e in ents[:-1])
    if o+tot+tail!=len(pl): stats['fit_fail']+=1; bad.append(f); continue
    stats['ok']+=1
print(stats.most_common()); print("bad:",len(bad)); print(bad[:5])
