import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
stats=collections.Counter()
for f in files:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': continue
    ln=struct.unpack('>I',d[4:8])[0]; pl=d[8:ln]
    f8,tail=struct.unpack('<II',pl[:8]); o=8; ents=[]
    while o+16<=len(pl):
        fl=pl[o:o+8]; h,l=struct.unpack('<II',pl[o+8:o+16]); ents.append((fl.hex(),h,l)); o+=16
        if h==0x70707070: break
    tot=sum(e[2] for e in ents[:-1]); ds=o
    stats[(ds+tot+tail)-len(pl)]+=1
print("residual (ds+sum+tail-len) histogram:",stats.most_common(10))
