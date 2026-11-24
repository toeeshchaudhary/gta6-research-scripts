import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
h=collections.Counter(); ex=[]
for f in files:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: h['nols']+=1; continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]
    body=d[i+8:i+ln]
    if len(body)<16: h['tiny']+=1; continue
    root,rt,n,nz=struct.unpack('<IIII',body[:16])
    if n>64 or n==0: h[('badn',n)]+=1; continue
    recs=[]
    o=16; ok=True
    for k in range(n):
        if o+32>len(body): ok=False;break
        if body[o+8:o+16]!=b'\xaa'*8: ok=False;break
        b1,b2,name,h2=struct.unpack('<IIII',body[o+16:o+32])
        recs.append((b1,b2,name,h2)); o+=32
    if not ok: h['badrec']+=1; continue
    cnt=[(x[1]>>8) for x in recs]
    lens=[(x[0]>>24) for x in recs]
    need=o+sum(cnt)*16
    h[('fit',len(body)-need, sum(1 for c in cnt if c>60), n)]+=1
print(len(files))
for k,v in h.most_common(14): print(v,k)
