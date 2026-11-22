import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
res=collections.Counter(); exact=0; ex=[]
for f in files[:500]:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': continue
    ln=struct.unpack('>I',d[4:8])[0]
    pl=d[8:ln]
    root,N=struct.unpack('<II',pl[:8])
    if 8+N*16>len(pl): res['trunc']+=1; continue
    ents=[]
    for i in range(N):
        o=8+i*16
        ents.append(struct.unpack('<III',pl[o+4:o+16]))
    last=ents[-1] if ents else None
    pred=8+N*16+sum(e[1] for e in ents[:-1])
    res['exact' if pred==len(pl) else 'off']+=1
    if pred==len(pl): exact+=1
    else: ex.append((os.path.basename(f),len(pl),N,pred,ents[-1][0],ents[-1][1]))
print("exact",exact)
for k,v in res.most_common(): print(v,k)
print(ex[:6])
