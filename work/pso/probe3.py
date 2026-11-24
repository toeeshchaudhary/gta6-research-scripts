import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
c8=collections.Counter(); c12=collections.Counter()
n=0
for f in files:
    d=open(f,'rb').read()
    if d[:4]!=b'PSIN' or len(d)<16: continue
    a,b=struct.unpack('<II',d[8:16])
    c8[a]+=1; c12[b]+=1; n+=1
print("files",n)
print("f8 top:",c8.most_common(6))
print("f12 top:",c12.most_common(6))
print("f12 distinct",len(c12),"f8 distinct",len(c8))
