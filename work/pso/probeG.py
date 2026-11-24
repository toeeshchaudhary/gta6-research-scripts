import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
first=collections.Counter(); other=collections.Counter()
lz=collections.Counter(); l3=collections.Counter(); l1=collections.Counter()
ex=[]
for f in files[:400]:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    n=body[9] if len(body)>15 else 0
    if not (0<n<=40): continue
    o=16; recs=[]; ok=True
    for k in range(n):
        if o+32>len(body) or body[o:o+8]!=b'\xaa'*8: ok=False;break
        recs.append((body[o+8],struct.unpack('<H',body[o+14:o+16])[0],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
    if not ok: continue
    for (sl,cnt,nm) in recs:
        for e in range(cnt):
            p=o
            if p+16>len(body): break
            L=struct.unpack('<IIII',body[p:p+16]); o+=16
            if e==0: first[L[0]>0x10000]+=1
            else:
                other[L[0]>0x10000]+=1
                if L[0]>0x10000:
                    lz[L[2]>0x10000]+=1
                    l1[L[1]]+=1; l3[L[3]]+=1
                    if len(ex)<10: ex.append((' '.join('%08x'%x for x in L), '0x%x'%nm))
print("first lane0>0x10000:",first.most_common())
print("other lane0>0x10000:",other.most_common())
print("among hash-named: lane2>0x10000:",lz.most_common())
print("lane1 common:",l1.most_common(8))
print("lane3 common:",l3.most_common(8))
for e in ex: print(e)
