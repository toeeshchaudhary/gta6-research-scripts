import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
rootin=0; tot=0; mism=0; blocks=0
for f in files:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    root=struct.unpack('<I',body[:4])[0]
    o=16; names=set()
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        names.add(struct.unpack('<I',body[o+16:o+20])[0]); o+=32
    tot+=1
    if root in names: rootin+=1
    # block vs structlen
    p=d.find(b'PSIN'); l2=struct.unpack('>I',d[4:8])[0]; pl=d[8:l2]
    f8,tail=struct.unpack('<II',pl[:8]); oo=8; ents=[]
    while oo+16<=len(pl):
        h,l=struct.unpack('<II',pl[oo+8:oo+16]); oo+=16
        if h==0x70707070: break
        ents.append((h,l))
    sl={}
    o=16
    while o+32<=len(body) and body[o:o+8]==b'\xaa'*8:
        sl[struct.unpack('<I',body[o+16:o+20])[0]]=struct.unpack('<H',body[o+8:o+10])[0]; o+=32
    for h,l in ents:
        blocks+=1
        if h in sl and sl[h]>0 and l % sl[h]: mism+=1
print("files",tot,"root defined in own LSCH",rootin,"(%.1f%%)"%(100*rootin/max(1,tot)))
print("blocks",blocks,"length not multiple of structLen",mism)
