import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
h=collections.Counter(); ex=[]
for f in files:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]
    body=d[i+8:i+ln]
    if len(body)<16: h['tiny']+=1; continue
    root,rt,nz,n=struct.unpack('<IIII',body[:16])
    n=n>>8
    if n>64 or n==0: h[('badn',n)]+=1; continue
    o=16; recs=[]; ok=True
    for k in range(n):
        if o+32>len(body): ok=False;break
        if body[o+8:o+16]!=b'\xaa'*8: ok=False;break
        b1,b2,name,h2=struct.unpack('<IIII',body[o+16:o+32])
        recs.append((b1>>24,b2>>8,name,h2)); o+=32
    if not ok: h['badrec']+=1; continue
    need=o+sum(r[1] for r in recs)*16
    h[len(body)-need]+=1
    if len(body)-need not in (0,8,16) and len(ex)<6: ex.append((os.path.basename(f),len(body),n,[r[1] for r in recs]))
print("residual:",h.most_common(10))
print(ex)
