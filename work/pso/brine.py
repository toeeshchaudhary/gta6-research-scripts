import itertools
def joaat(s, seed=0xB779A091):
    h=seed
    for ch in s.encode('utf-8'):
        h=(h+ch)&0xFFFFFFFF; h=(h+(h<<10))&0xFFFFFFFF; h^=h>>6
    h=(h+(h<<3))&0xFFFFFFFF; h^=h>>11; h=(h+(h<<15))&0xFFFFFFFF
    return h
targets={0xDE396FE2,0x20151CEA,0x85B4C631,0xAEB623D8,0x01393259,0xFE4614E3,0x4427C39F,0x3FAC7FC1}
pre=['grc','grcState','grcx','sga','gpu','rage','rmc','pgp','pg','gr','gfx','grcPipeline','grcRender','grcSetup']
core=['Blend','BlendState','BlendStateDesc','DepthStencil','DepthStencilState','DepthStencilStateDesc',
 'Rasterizer','RasterizerState','RasterizerStateDesc','RenderTarget','RenderTargetState','RenderTargetStateDesc',
 'Pipeline','PipelineDesc','PipelineState','VertexDeclaration','VertexDecl','VertexDeclarationDesc',
 'Shader','ShaderState','Sampler','SamplerState','Stream','Geometry','Draw','DrawParams','StateBlock','Desc','State']
suf=['','_','Desc','State','Info','Block','Params','_Desc','BlockDesc','.desc','Desc_','s','Type']
cands=set()
for p in pre:
    for c in core:
        for s in suf:
            cands.add(p+c+s)
            cands.add(p+'::'+c+s)
            cands.add(p.capitalize()+c+s)
for c in core:
    for s in suf: cands.add(c+s)
hits=[]
for c in cands:
    for seed in (0xB779A091,0x3FAC7125,0):
        v=joaat(c,seed)
        if v in targets: hits.append((hex(v),c,hex(seed)))
print(len(cands),"candidates")
for h in hits: print(h)
