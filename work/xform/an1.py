import struct, os, glob, collections, math

OUT=r"work\xform\out"
WHDR=16
def load_tables(prefix):
    tabs=[]
    for f in sorted(glob.glob(os.path.join(OUT, prefix+"_*.bin"))):
        if "_done" in f: continue
        d=open(f,"rb").read()
        p=0
        while p+WHDR<=len(d):
            res,start,n=struct.unpack("<III",d[p:p+12])
            kind=d[p+12]
            p+=WHDR
            body=d[p:p+n*80]; p+=n*80
            if len(body)<n*80: break
            tabs.append((res,start,n,kind,body))
    return tabs

def merge(tabs):
    # merge contiguous tables of the same kind in the same resource
    by=collections.defaultdict(list)
    for res,start,n,kind,body in tabs: by[(res,kind)].append((start,n,body))
    out=[]
    for (res,kind),lst in by.items():
        lst.sort()
        cur=None
        for start,n,body in lst:
            if cur and cur[0]+cur[1]*80==start:
                cur[2]+=body; cur[1]+=n
            else:
                if cur: out.append((res,cur[0],cur[1],kind,cur[2]))
                cur=[start,n,body]
        if cur: out.append((res,cur[0],cur[1],kind,cur[2]))
    return out

def wrecords(res,body):
    recs=[]
    for i in range(len(body)//80):
        r=body[i*80:(i+1)*80]
        pos=struct.unpack("<3f",r[0:12]); yaw=struct.unpack("<f",r[12:16])[0]
        en=(struct.unpack("<I",r[0x10:0x14])[0], struct.unpack("<I",r[0x14:0x18])[0])
        ids=struct.unpack("<4I",r[0x20:0x30])
        recs.append((pos,yaw,en,ids))
    return recs

if __name__=="__main__":
    for f,name in (("109C363010","109C363010"),("109BDDA010","109BDDA010")):
        pass
    tabs=load_tables("all")
    print("raw tables", len(tabs))
    m=merge(tabs)
    print("merged tables", len(m))
    kinds=collections.Counter(t[3] for t in m)
    print("by kind", kinds)
    tot=collections.Counter()
    for res,start,n,kind,body in m: tot[kind]+=n
    print("records by kind", tot)
    wres=set(res for res,_,_,k,_ in m if k==0)
    print("resources with W", len(wres))
    # position stats over W
    xs=[];ys=[];zs=[]
    for res,start,n,kind,body in m:
        if kind!=0: continue
        for i in range(n):
            r=body[i*80:(i+1)*80]
            x,y,z=struct.unpack("<3f",r[0:12]); xs.append(x);ys.append(y);zs.append(z)
    if xs:
        def q(v,p): 
            v=sorted(v); return v[int(p*(len(v)-1))]
        print("W x min/max %.1f/%.1f  q05/95 %.1f/%.1f"%(min(xs),max(xs),q(xs,0.05),q(xs,0.95)))
        print("W y min/max %.1f/%.1f  q05/95 %.1f/%.1f"%(min(ys),max(ys),q(ys,0.05),q(ys,0.95)))
        print("W z min/max %.1f/%.1f  q05/95 %.1f/%.1f"%(min(zs),max(zs),q(zs,0.05),q(zs,0.95)))
        zero=sum(1 for x,y,z in zip(xs,ys,zs) if x==0 and y==0 and z==0)
        print("W records at exactly (0,0,0):", zero, "/", len(xs))
