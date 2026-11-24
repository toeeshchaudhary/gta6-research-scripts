import struct
def load(p):
    b=open(p,"rb").read(); assert struct.unpack("<I",b[:4])[0]==0x314D5246
    nb=struct.unpack("<i",b[4:8])[0]; o=8; meta=[]
    for i in range(nb):
        pl=struct.unpack("<q",b[o:o+8])[0]; il=struct.unpack("<i",b[o+8:o+12])[0]; meta.append((pl,il)); o+=12
    blocks=[]; p=o
    for pl,il in meta: blocks.append(b[p:p+il]); p+=il
    return meta,blocks
def joaat(s):
    h=0
    for ch in s.lower():
        h=(h+ord(ch))&0xFFFFFFFF; h=(h+(h<<10))&0xFFFFFFFF; h^=h>>6
    h=(h+(h<<3))&0xFFFFFFFF; h^=h>>11
    return (h+(h<<15))&0xFFFFFFFF
def cstr(b,o):
    e=b.find(b"\x00",o)
    if e<0 or e-o>200: return None
    try: return b[o:e].decode("ascii")
    except: return None

for f in ("fe970B010","105F239010","109C363010"):
    meta,blocks=load("work\\xform\\out\\%s.bin"%f)
    b0=blocks[0]
    hits=[]
    for o in range(0,len(b0)-80):
        h=struct.unpack("<I",b0[o+0x0C:o+0x10])[0]
        if h<0x1000: continue
        p=struct.unpack("<I",b0[o+0x20:o+0x24])[0]
        if not (0x50000000<=p<0x51000000): continue
        s=cstr(b0,p-0x50000000)
        if s is None: continue
        if joaat(s)==h:
            hits.append((o,h,s))
    print("==",f,"block0",len(b0),"named-record hits:",len(hits))
    if hits:
        offs=[h[0] for h in hits]
        deltas={}
        for i in range(1,len(offs)): deltas[offs[i]-offs[i-1]]=deltas.get(offs[i]-offs[i-1],0)+1
        print("  top deltas:", sorted(deltas.items(), key=lambda kv:-kv[1])[:6])
        print("  first offsets:", offs[:6], "... last", offs[-3:])
        for o,h,s in hits[:4]:
            pos=struct.unpack("<3f",b0[o:o+12])
            rot=struct.unpack("<4f",b0[o+0x40:o+0x50])
            print("   0x%05X %08X pos=%s rot=%s %s"%(o,h,["%.3f"%v for v in pos],["%.3f"%v for v in rot],s))
