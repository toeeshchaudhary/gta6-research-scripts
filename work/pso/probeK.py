import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
types=collections.Counter(); laneX=collections.Counter(); offmax=collections.Counter(); refok=0; refn=0
sample=None
for f in files[:800]:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    o=16; recs=[]
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        recs.append((struct.unpack('<H',body[o+8:o+10])[0],struct.unpack('<H',body[o+14:o+16])[0],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
    if not recs: continue
    names={r[2] for r in recs}
    for (sl,cnt,nm) in recs:
        offs=[]
        for e in range(cnt):
            p=o
            if p+16>len(body): break
            n2,off,X,t,ref=struct.unpack('<IIHHI',body[p:p+16]); o+=16
            types[t]+=1; laneX[X]+=1; offs.append(off)
            if ref:
                refn+=1
                if ref in names or ref>=0x100: refok+=1
            if sample is None and sl>400: sample=(sl,cnt,offs)
        if offs: offmax[('maxoff<=len',max(offs)<=sl)]+=1
print("typeId:",types.most_common(20))
print("laneX:",laneX.most_common(8))
print("maxoff<=structLen:",offmax.most_common())
print("refKey resolvable:",refok,"/",refn)
if sample: print("sample struct: len",sample[0],"cnt",sample[1],"offs sorted",sorted(sample[2])[:40])
