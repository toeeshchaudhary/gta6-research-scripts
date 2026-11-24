import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
rem=collections.Counter(); tot=0
for f in files[:600]:
    d=open(f,'rb').read(); i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    o=16; sl={}
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        sl[struct.unpack('<I',body[o+16:o+20])[0]]=struct.unpack('<H',body[o+8:o+10])[0]; o+=32
    p=d.find(b'PSIN'); l2=struct.unpack('>I',d[4:8])[0]; pl=d[8:l2]
    f8,tail=struct.unpack('<II',pl[:8]); oo=8
    while oo+16<=len(pl):
        h,l=struct.unpack('<II',pl[oo+8:oo+16]); oo+=16
        if h==0x70707070: break
        tot+=1
        if h in sl and sl[h]:
            rem[l % sl[h]]+=1
print("blocks",tot)
print("length % structLen:",rem.most_common(10))
