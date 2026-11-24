import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
roots=collections.Counter(); rv=collections.Counter(); allnames=set(); rootbytes={}
for f in files:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    roots[struct.unpack('<I',body[:4])[0]]+=1
    rv[struct.unpack('<I',body[4:8])[0]]+=1
    rootbytes[struct.unpack('<I',body[:4])[0]]=body[:8].hex()
    o=16
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        allnames.add(struct.unpack('<I',body[o+16:o+20])[0]); o+=32
print("distinct roots",len(roots),"defined anywhere:",sum(1 for r in roots if r in allnames))
print("top roots:",[(hex(k),v) for k,v in roots.most_common(8)])
print("rootVersion distinct:",[(hex(k),v) for k,v in rv.most_common(5)])
print("distinct record names overall",len(allnames))
print("roots overlapping allnames sample:",[hex(r) for r in roots if r in allnames][:8])
