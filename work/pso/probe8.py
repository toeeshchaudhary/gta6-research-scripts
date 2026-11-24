import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
h=collections.Counter(); al=lambda n:(n+15)//16*16
ok=0
for f in files:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': continue
    ln=struct.unpack('>I',d[4:8])[0]
    if ln>len(d): h['trunc']+=1; continue
    pl=d[8:ln]
    if len(pl)<8: h['tiny']+=1; continue
    f8,tail=struct.unpack('<II',pl[:8]); o=8; ents=[]
    while o+16<=len(pl):
        fl=pl[o:o+8]; hh,l=struct.unpack('<II',pl[o+8:o+16]); ents.append((fl.hex(),hh,l)); o+=16
        if hh==0x70707070: break
    if not ents or ents[-1][1]!=0x70707070: h['noterm']+=1; continue
    tot=sum(al(e[2]) for e in ents[:-1])
    need=o+tot+tail
    if len(pl)>=need and len(pl)-need<=15 and (8+len(pl))%16==0: h['ok']+=1; ok+=1
    else: h[('bad',len(pl)-need,(8+len(pl))%16)]+=1
print(h.most_common(8)); print("ok",ok,"of",len(files))
