import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
size=collections.defaultdict(collections.Counter); arr=collections.defaultdict(collections.Counter)
for f in files:
    d=open(f,'rb').read(); i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    o=16; recs=[]
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        recs.append((struct.unpack('<H',body[o+8:o+10])[0],struct.unpack('<H',body[o+14:o+16])[0])); o+=32
    for (sl,cnt) in recs:
        fs=[]
        for e in range(cnt):
            p=o
            if p+16>len(body): break
            t,off,al,tc,ref=struct.unpack('<IIHHI',body[p:p+16]); o+=16
            fs.append((off,t,al,tc,ref))
        fs.sort()
        for k,(off,t,al,tc,ref) in enumerate(fs):
            arr[t][al]+=1
            if k+1<len(fs): size[t][fs[k+1][0]-off]+=1
            elif sl>=off: size[t][sl-off]+=1
print("distinct types",len(size))
for t in sorted(size, key=lambda x:-sum(size[x].values()))[:28]:
    print("%08x size=%s arrlen=%s n=%d ref=%d"%(t,size[t].most_common(2),arr[t].most_common(2),sum(size[t].values()),sum(arr[t].values())))
