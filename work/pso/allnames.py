import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
info=collections.Counter()
for f in files:
    d=open(f,'rb').read(); i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    o=16
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        info[(struct.unpack('<I',body[o+16:o+20])[0],struct.unpack('<H',body[o+8:o+10])[0],struct.unpack('<H',body[o+14:o+16])[0])]+=1; o+=32
for (n,l,c),k in sorted(info.items(), key=lambda kv:-kv[1]):
    print("%08x len=%-5d cnt=%-4d files=%d"%(n,l,c,k))
