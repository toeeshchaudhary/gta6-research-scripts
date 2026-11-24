import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
h=collections.Counter(); ex=[]
for f in files:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    if len(body)<16: h['tiny']+=1; continue
    n=body[9]
    if n>60 or n==0: h['badn']+=1; continue
    o=16; recs=[]; ok=True
    for k in range(n):
        if o+32>len(body) or body[o:o+8]!=b'\xaa'*8: ok=False; break
        recs.append((struct.unpack('<I',body[o+8:o+12])[0],struct.unpack('<H',body[o+14:o+16])[0],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
    if not ok: h['badrec']+=1; continue
    if o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        nm=struct.unpack('<I',body[o+16:o+20])[0]
        if nm==0x100:
            recs.append((struct.unpack('<I',body[o+8:o+12])[0],struct.unpack('<H',body[o+14:o+16])[0],nm)); o+=32
    ents=sum(r[1] for r in recs)-1
    need=o+ents*16
    h[len(body)-need]+=1
    if len(body)-need and len(ex)<6: ex.append((os.path.basename(f),len(body),n,[r[1] for r in recs],len(body)-need))
print(h.most_common(6)); print(ex)
