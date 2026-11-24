import struct,glob,os
allf=sorted(glob.glob(r'work\scripts\out\script_pages\*.bin'))
files=[]
for f in allf:
    with open(f,'rb') as h: 
        if h.read(4)==b'PSIN': files.append(f)
    if len(files)>=14: break
for f in files:
    d=open(f,'rb').read()
    l2=struct.unpack('>I',d[4:8])[0]; pl=d[8:l2]
    i=pl.find(b'LSCH'); ln=struct.unpack('>I',pl[i+4:i+8])[0]; body=pl[i+8:i+ln]
    o=16; recs=[]
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        recs.append((struct.unpack('<H',body[o+8:o+10])[0],struct.unpack('<H',body[o+14:o+16])[0],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
    f8,tail=struct.unpack('<II',pl[:8]); oo=8; ents=[]
    while oo+16<=len(pl):
        h,l=struct.unpack('<II',pl[oo+8:oo+16]); oo+=16
        if h==0x70707070: break
        ents.append((h,l))
    desc={n:(l,c) for l,c,n in recs}
    print(os.path.basename(f), "u0=%d"%f8, "root=%08x"%struct.unpack('<I',body[:4])[0], "enums=%d"%(len(pl)-0))
    for h,l in ents:
        d2=desc.get(h)
        print("   block %08x len=%d %s"%(h,l,("structlen=%d cnt=%d"%(d2[0],d2[1])) if d2 else "UNRESOLVED"))
