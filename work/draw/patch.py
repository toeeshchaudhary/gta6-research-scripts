import subprocess,re
p=r'work/draw/pdecode.py'
s=open(p,encoding='utf-8').read()
s=s.replace("""            cf = U32(idx, 0); tris = U32(idx, 4); refs = U32(idx, 8)""","""            cf = U32(idx, 0); tris = U32(idx, 4); refs = U32(idx, 8)
            print('  ib at',iat,'ilen',ilen,'gf x',len(gfx),'cf',hex(cf),'tris',tris,'refs',refs,'desc+8',U16(sysb,desc+8),'desc+10',U16(sysb,desc+10),'binding',hex(U32(sysb,desc+12)))""")
open(p,'w',encoding='utf-8').write(s)
