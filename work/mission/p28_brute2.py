import struct,math
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read();n=len(b)
def recs(off,size,skip=16):
    return [struct.unpack_from('<8I',b,i) for i in range(off+skip,off+size-15,32)]
def score(rs,base,unit):
    tot=0.0
    for d in rs:
        cnt=d[4]&0xffff; off=d[4]>>16
        o=base+off*unit
        if o<0 or o+cnt*4>n: return -1
        good=0
        for k in range(cnt):
            v=struct.unpack_from('<f',b,o+4*k)[0]
            if math.isfinite(v) and (v==0 or 1e-6<abs(v)<1e6): good+=1
        tot+=good/cnt
    return tot/len(rs)
for name,off,size in [('0109',11248,448),('010b',33776,224),('010d',38032,224),('010f',51984,224),('0111',53552,224),('0113',84688,224)]:
    rs=recs(off,size)
    maxk=max((d[4]>>16) for d in rs)
    res=[]
    for unit in (1,4):
        lim=n-maxk*unit-4096
        if lim<0: continue
        for base in range(0,lim,4):
            s=score(rs,base,unit)
            if s>0: res.append((s,base,unit))
    res.sort(reverse=True)
    print(name,[(round(s,2),hex(bb),u) for s,bb,u in res[:6]],flush=True)
