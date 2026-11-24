import struct
p='work/pso/samples/a.bin'
d=open(p,'rb').read(); i=d.find(b'LSCH'); ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
o=16; recs=[]
while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
    recs.append((struct.unpack('<H',body[o+8:o+10])[0],struct.unpack('<H',body[o+14:o+16])[0],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
print("recs",[(hex(n),l,c) for l,c,n in recs])
tot=sum(c for _,c,_ in recs)-1
print("total fields",tot,"body",len(body),"offset",o)
for k in range(tot):
    t,off,a,b,ref=struct.unpack('<IIHHI',body[o+k*16:o+k*16+16])
    print("f%-3d type=%08x off=%-4d u16a=%-5d u16b=%-3d ref=%08x"%(k,t,off,a,b,ref))
