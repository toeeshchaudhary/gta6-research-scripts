import struct
p=r'work\scripts\out\story_groups\g0000_03150000.bin'
d=open(p,'rb').read(); i=d.find(b'LSCH'); ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
o=16; recs=[]
while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
    recs.append((struct.unpack('<H',body[o+8:o+10])[0],struct.unpack('<H',body[o+14:o+16])[0],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
print("records",len(recs),"first rec len,cnt,name",recs[0])
sl,cnt,nm=recs[0]
for e in range(min(cnt,40)):
    t,off,a,b,ref=struct.unpack('<IIHHI',body[o+e*16:o+e*16+16])
    print("e%-3d type=%08x off=%-4d u16a=%-6d u16b=%-3d ref=%08x"%(e,t,off,a,b,ref))
