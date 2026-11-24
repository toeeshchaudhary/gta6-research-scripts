import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
h=collections.Counter(); ex=[]; names=collections.Counter(); lens=collections.Counter()
for f in files:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]
    body=d[i+8:i+ln]
    if len(body)<16: h['tiny']+=1; continue
    n=body[9]
    if n>80 or n==0: h[('badn',n)]+=1; continue
    o=16; recs=[]; ok=True
    for k in range(n):
        if o+32>len(body): ok=False;break
        pad=body[o:o+8]
        if pad!=b'\xaa'*8: ok=False; ex.append(('pad',os.path.basename(f),pad.hex())); break
        recs.append((body[o+8],body[o+14],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
    if not ok: h['badrec']+=1; continue
    for r in recs: names[r[2]]+=1; lens[r[0]]+=1
    res=len(body)-(o+sum(r[1] for r in recs)*16)
    h[res]+=1
    if len(ex)<6 and res!=0: ex.append((os.path.basename(f),len(body),n,[r[1] for r in recs],res))
print("residual:",h.most_common(8)); print(ex[:4])
print("names:",[(hex(k),v) for k,v in names.most_common(8)])
print("lens:",lens.most_common(8))
