import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
pair=collections.Counter(); bytype=collections.defaultdict(list)
for f in files[:800]:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    o=16; recs=[]
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        recs.append((struct.unpack('<H',body[o+8:o+10])[0],struct.unpack('<H',body[o+14:o+16])[0])); o+=32
    for (sl,cnt) in recs:
        for e in range(cnt):
            p=o
            if p+16>len(body): break
            n2,off,X,t,ref=struct.unpack('<IIHHI',body[p:p+16]); o+=16
            pair[(X,t)]+=1
            if len(bytype[X])<40: bytype[X].append((off,t,ref,sl))
print("(X,typeCode) pairs:",pair.most_common(16))
for X,v in sorted(bytype.items()):
    print(hex(X),"n=",pair.get((X,0),0)+sum(c for (a,b),c in pair.items() if a==X and b!=0),"sample:",v[:8])
