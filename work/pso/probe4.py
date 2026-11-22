import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
stats=collections.Counter(); bad=[]; nent=collections.Counter(); tailfiller=collections.Counter()
for f in files:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': stats['nomagic']+=1; continue
    ln=struct.unpack('>I',d[4:8])[0]
    if ln!=len(d) and ln>len(d): stats['lenMismatch']+=1; continue
    pl=d[8:ln]
    f8,tail=struct.unpack('<II',pl[:8])
    o=8; ents=[]
    while o+16<=len(pl):
        fl=pl[o:o+8]; h,l=struct.unpack('<II',pl[o+8:o+16])
        ents.append((fl.hex(),h,l)); o+=16
        if h==0x70707070: break
    if not ents or ents[-1][1]!=0x70707070: stats['noterm']+=1; bad.append((f,'noterm')); continue
    if any(e[0]!='a'*16 for e in ents[:-1]): stats['badfill']+=1; bad.append((f,'fill')); continue
    datastart=o; total=sum(e[2] for e in ents[:-1])
    if datastart+total+tail != len(pl):
        stats['fit_fail']+=1
        if len(bad)<8: bad.append((f,datastart,total,tail,len(pl)))
        continue
    stats['ok']+=1; nent[len(ents)-1]+=1
    tailfiller[pl[-tail:-tail+8].hex() if tail>=8 else 'lt8']+=1
print(stats.most_common())
print("entries dist",nent.most_common(10))
print("tail first8 top",tailfiller.most_common(6))
print(bad[:8])
