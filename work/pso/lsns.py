import glob,struct,os,collections
files=sorted(glob.glob(r'work\story_groups\*.bin'))  # dummy
files=[]
for d in (r'work\scripts\out\story_groups',r'work\scripts\out\script_pages'):
    files+=glob.glob(os.path.join(d,'*.bin'))
asc=0; tot=0; hdr=collections.Counter(); n=0
for f in files:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN': continue
    i=d.find(b'LSNS')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; pl=d[i+8:i+ln]
    n+=1; tot+=len(pl)
    asc+=sum(1 for b in pl if 32<=b<127)
    if len(pl)>=12: hdr[pl[:12].hex()]+=1
    if n>=300: break
print("LSNS blobs",n,"bytes",tot,"printable frac %.4f"%(asc/max(1,tot)))
print("first-12-byte headers:",hdr.most_common(5))
