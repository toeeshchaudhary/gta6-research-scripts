def joaat(s, seed=0):
    h=seed
    for ch in s.encode('utf-8'):
        h=(h+ch)&0xFFFFFFFF; h=(h+(h<<10))&0xFFFFFFFF; h^=h>>6
    h=(h+(h<<3))&0xFFFFFFFF; h^=h>>11; h=(h+(h<<15))&0xFFFFFFFF
    return h
targets={0xDE396FE2,0x20151CEA,0x85B4C631,0xAEB623D8,0x01393259,0xFE4614E3,0x4427C39F,0x3FAC7FC1}
pre=['grc','grcx','sga','gpu','rage','rmc','pgp','pg','gfx','','rage__','grc__','rage___']
core=['Blend','BlendState','BlendStateDesc','DepthStencil','DepthStencilState','DepthStencilStateDesc','Rasterizer','RasterizerState','RasterizerStateDesc','RenderTarget','RenderTargetState','RenderTargetStateDesc','Pipeline','PipelineDesc','PipelineState','VertexDeclaration','VertexDecl','Shader','Sampler','SamplerState','Stream','Geometry','Draw','DrawParams','StateBlock','Desc','State','Desc__']
hits=[]
seen=set()
for p in pre:
    for c in core:
        for s in ('','Desc','State','Info','__'):
            for sep in ('','_','__'):
                name=(p+sep+c+s).lower()
                if name in seen: continue
                seen.add(name)
                v=joaat(name)
                if v in targets: hits.append((hex(v),name))
print(len(seen))
for h in hits: print(h)
# sanity
print("joaat('test')=0x%08X"%joaat("test"))
