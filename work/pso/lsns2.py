import glob,struct,collections
c=collections.Counter()
for f in glob.glob(r'work\scripts\out\story_groups\*.bin')[:200]:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': continue
    i=d.find(b'LSNS'); ln=struct.unpack('>I',d[i+4:i+8])[0]; pl=d[i+8:i+ln]
    if len(pl)>=12: c[(pl[4:8].hex(), len(pl)-12==struct.unpack('<I',pl[8:12])[0])]+=1
print(c.most_common(5))
