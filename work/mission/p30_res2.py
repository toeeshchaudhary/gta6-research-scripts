def joaat(s):
    h=0
    for c in s.lower().encode('latin-1','replace'):
        h=(h+c)&0xFFFFFFFF; h=(h+(h<<10))&0xFFFFFFFF; h^=h>>6
    h=(h+(h<<3))&0xFFFFFFFF; h^=h>>11
    return (h+(h<<15))&0xFFFFFFFF
d={}
for l in open(r'.\work\story\s17_repeated_keys.txt',encoding='utf-8',errors='replace').read().splitlines():
    if not l.strip(): continue
    a=l.split('\t'); d[int(a[0],16)]=a[2] if len(a)>2 else ''
for s in open(r'.\work\story\missions_common_rpf.txt',encoding='utf-8').read().split():
    d.setdefault(joaat(s),'MISSION:'+s)
for h in [0x0bfc15e3,0x5ff2ee55,0x6081d83f,0xd1c59792,0xe0a622df,0xfea625c9,0xf48399a5,0x03d9a997,0x10eb3241,0x59ff84a0,0x65837dc9,0x4e347117,0x6dbfa927,0x013697cd,0x0308d2d5,0x9c95b1cd,0x81a1a2a7,0xd0bad08b,0x80553f47,0x0f3f2e1d,0x467f7f84,0x5a8e1b4d,0x9ab673d8,0xad672199,0xb187b7f8]:
    print('%08x %s'%(h,d.get(h,'-')))
