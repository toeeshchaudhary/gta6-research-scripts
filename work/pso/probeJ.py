import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
h=collections.Counter(); ex=[]; nn=collections.Counter(); unk=collections.Counter()
for f in files:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    if len(body)<16: h['tiny']+=1; continue
    unk[body[9]]+=1
    o=16; recs=[]; ok=True
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        recs.append((struct.unpack('<H',body[o+8:o+10])[0],struct.unpack('<H',body[o+14:o+16])[0],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
        if len(recs)>400: ok=False;break
    if not ok or not recs: h['badrec']+=1; continue
    nn[len(recs)]+=1
    ents=sum(r[1] for r in recs)-1
    res=len(body)-(o+ents*16)
    h[res]+=1
    if res and len(ex)<6: ex.append((os.path.basename(f),len(body),len(recs),ents,res))
print("residual:",h.most_common(6)); print("records/file:",nn.most_common(5)); print("body9:",unk.most_common(3)); print(ex)
