import struct, collections
b=open(r"work\xform\out\E443EF6010.bin","rb").read()
nb=struct.unpack("<i",b[4:8])[0]; o=8; meta=[]
for i in range(nb):
    pl=struct.unpack("<q",b[o:o+8])[0]; il=struct.unpack("<i",b[o+8:o+12])[0]; meta.append((pl,il)); o+=12
p=o; bl=[]
for pl,il in meta: bl.append(b[p:p+il]); p+=il
b0=bl[0]
print("len",len(b0))
for start in (0x60,):
    cols=collections.defaultdict(collections.Counter)
    N=600
    for i in range(N):
        r=start+i*80
        for k in range(20):
            cols[k][struct.unpack("<I",b0[r+4*k:r+4*k+4])[0]]+=1
    for k in sorted(cols):
        cc=cols[k]
        print("  +0x%02X distinct=%-5d top=%s"%(4*k,len(cc),[(hex(v) if v>0xFFFF else v,n) for v,n in cc.most_common(3)]))
