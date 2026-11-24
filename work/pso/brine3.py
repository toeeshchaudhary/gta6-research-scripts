def joaat(s, seed=0):
    h=seed
    for ch in s.encode('utf-8'):
        h=(h+ch)&0xFFFFFFFF; h=(h+(h<<10))&0xFFFFFFFF; h^=h>>6
    h=(h+(h<<3))&0xFFFFFFFF; h^=h>>11; h=(h+(h<<15))&0xFFFFFFFF
    return h
targets={0x01296AED:2,0x0333F0AF:2,0x2260B8BE:16,0x2A8E416F:1,0x31A7C9F6:3,0x3579A1EE:4,0x4880F687:16,0x5C2411E5:16,0x79754B03:1,0x80800E19:4,0x81B35C5C:4,0x93BAB68E:4,0xD54B8545:16,0xE6E17F14:16,0xF3394B19:2}
# recompute a couple from the size table
names=['bool','u8','u16','u32','u64','s8','s16','s32','s64','float','f16','f32','f64','Vector2','Vector3','Vector4','Vector3A','Vector4A','Matrix34','Matrix43','Matrix44','Vector2f','Vector3f','Vector4f','UInt8','UInt16','UInt32','UInt64','Int8','Int16','Int32','Int64','Bool','Byte','UByte','SByte','Half','HFloat','Long','String','Char','Hash','MetaHash','RageHash','Color32','Matrix','Vector','Vec2','Vec3','Vec4','float2','float3','float4','uint8','uint16','uint32','uint64','int8','int16','int32','pbuffer','pointer','Pointer','ARRAYINFO','Array']
hits=[]
for n in names:
    for seed in (0,0xB779A091):
        for f in (lambda x:x, lambda x:x.lower(), lambda x:x.upper(), lambda x:x.capitalize()):
            s=f(n); v=joaat(s,seed)
            if v in targets: hits.append((hex(v),s,hex(seed),targets[v]))
print(len(hits))
for h in hits: print(h)
print("sample: joaat('u32',0)=%08x joaat('float',0)=%08x joaat('Vector4',0)=%08x"%(joaat('u32'),joaat('float'),joaat('Vector4')))
