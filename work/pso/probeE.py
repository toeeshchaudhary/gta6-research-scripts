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
    n=body[9] if len(body)>15 else 0
    if n>80 or n==0: h['badn']+=1; continue
    o=16; recs=[]; ok=True
    for k in range(n):
        if o+32>len(body) or body[o:o+8]!=b'\xaa'*8: ok=False;break
        recs.append((body[o+8],body[o+14],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
    if not ok: h['badrec']+=1; continue
    arr = recs[-1][2]==0x100
    ents=sum(r[1] for r in recs)-(1 if arr else 0)
    need=o+(0 if arr else 16)+ents*16
    res=len(body)-need
    h[res]+=1
    if res!=0 and len(ex)<8: ex.append((os.path.basename(f),len(body),n,[r[1] for r in recs],res))
print(h.most_common(8)); print(ex[:5])
