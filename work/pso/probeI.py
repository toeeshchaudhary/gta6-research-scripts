import struct,sys
p=r'work\scripts\out\story_groups\g0000_03150000.bin'
d=open(p,'rb').read()
i=d.find(b'LSCH'); ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
aa=b'\xaa'*8
offs=[k for k in range(len(body)-8) if body[k:k+8]==aa]
print("AAAA count",len(offs),"first",offs[:10])
recs=[]
for o in offs:
    if o+32<=len(body):
        sl=struct.unpack('<H',body[o+8:o+10])[0]; cnt=struct.unpack('<H',body[o+14:o+16])[0]; nm=struct.unpack('<I',body[o+16:o+20])[0]
        recs.append((o,sl,cnt,nm))
for r in recs[:12]: print("rec @%d len=%d cnt=%d name=%08x"%r)
print("...")
for r in recs[-6:]: print("rec @%d len=%d cnt=%d name=%08x"%r)
print("body len",len(body))
