import struct,math
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read();n=len(b)
def plaus(off,cnt):
    if off+4*cnt>n or off<0: return -1
    good=0
    for k in range(cnt):
        v=struct.unpack_from('<f',b,off+4*k)[0]
        if math.isfinite(v) and (v==0 or 1e-6<abs(v)<1e6): good+=1
    return good/cnt
def table(src_off,size):
    out=[]
    for i in range(src_off,src_off+size,32):
        d=struct.unpack_from('<8I',b,i); out.append((d[0],d[2],d[4]&0xffff,d[4]>>16,d[6]))
    return out
def score(recs,base,unit):
    s=0
    for key,c,lo,hi,pair in recs:
        r=plaus(base+hi*unit,lo)
        if r<0: return -1
        s+=r
    return s/len(recs)
for name,off,size in [('0109',11248,448),('010d',38032,224),('010f',51984,224),('0111',53552,224),('0113',84688,224)]:
    recs=table(off,size)
    best=[]
    for unit in (1,2,4):
        for base in range(0,n-4096,4):
            sc=score(recs,base,unit)
            best.append((sc,base,unit))
    best.sort(reverse=True)
    print(name,[(round(s,2),hex(bb),u) for s,bb,u in best[:5]])
