import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
h=collections.Counter(); ex=[]; recfill=collections.Counter()
for f in files:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]
    body=d[i+8:i+ln]
    if len(body)<16: h['tiny']+=1; continue
    root,rt=struct.unpack('<II',body[:8])
    n=struct.unpack('<I',body[8:12])[0]; nz=struct.unpack('<I',body[12:16])[0]; n=n>>8
    if n>80 or n==0 or nz!=0: h[('badn',n,nz)]+=1; continue
    o=16; recs=[]; ok=True
    for k in range(n):
        if o+32>len(body): ok=False;break
        pad=body[o:o+8]; 
        if pad!=b'\xaa'*8: ok=False; recfill[pad.hex()]+=1; break
        b1,b2,name,h2=struct.unpack('<IIII',body[o+16:o+32])
        recs.append((b1>>24,b2>>8,name,h2)); o+=32
    if not ok: h['badrec']+=1; continue
    need=o+sum(r[1] for r in recs)*16
    h[len(body)-need]+=1
    if len(body)-need not in (0,8,16) and len(ex)<6: ex.append((os.path.basename(f),len(body),n,[r[1] for r in recs]))
print("residual:",h.most_common(10)); print(ex); print("recfill",recfill.most_common(3))
