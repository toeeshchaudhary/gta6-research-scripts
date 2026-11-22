exec(open(r'work/draw/chain.py').read())
length = len(system) - d
stubAt = (length + 15) & ~15
buf = bytearray(system[d:]) + bytearray(stubAt + 64 - length)
for i in range(0, length - 7, 8):
    v = struct.unpack_from('<Q', buf, i)[0]
    if v < 0x50000000: continue
    o = v - 0x50000000
    if o > len(system) or o < d: continue
    struct.pack_into('<Q', buf, i, v - d)
struct.pack_into('<Q', buf, 8, 0x50000000 + stubAt)
buf[stubAt+8]=1; buf[stubAt+9]=1
sysb=bytes(buf)
print('wrapped len',len(sysb),'stub',hex(stubAt))
src=open(r'work/draw/replica.py').read()
start=src.index("MAXSYS")
end=src.index("print('looks_drawable'")
exec(src[start:end])
print('looks_drawable', looks_drawable(sysb))
try:
    Cover(0,176); pages=S(8,16); sp,gp=sysb[pages+8],sysb[pages+9]
    Check(0<sp<=32 and 0<gp<=32,'page counts'); Cover(pages,16+8*(sp+gp))
    print('name',Name(168)); lod=S(80,16); models=U16(lod+8)
    Check(0<models<=256 and models==U16(lod+10),'models'); print('models',models)
    ptrs=S(lod,models*8)
    for mi in range(models):
        model=S(ptrs+mi*8,56); cnt=U16(model+16)
        Check(0<cnt<=256 and cnt==U16(model+18) and cnt==U16(model+54),'geomcnt')
        geos=S(model+8,cnt*8); S(model+24,(cnt+(1 if cnt>1 else 0))*32)
        for i2 in range(cnt):
            g=S(geos+i2*8,160); vb=S(g+8,80); fvf=S(vb+64,320)
            flags=U32(fvf+0x138); vc=flags>>10; size,fmt=sysb[fvf+0xD0],sysb[fvf+0x104]
            Check((flags&1)!=0 and 0<vc<=1000000,'vf'); Check((size==12 and fmt==6) or (size==8 and fmt==16),'fmt')
            b=U32(vb+8)*U16(vb+12); off2=U32(fvf); Check(96<=off2<=b and vc*size<=b-off2,'range')
            Buffer(vb); desc=S(g+64,16); ib=S(desc,64); Check(U16(ib+12)==4,'idx'); Buffer(ib)
    print('PROBE OK')
except Exception as e:
    print('PROBE FAIL',e)
