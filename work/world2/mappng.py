import json,zlib,struct,os
p='work/world2/out/scene_world_full.json'
d=json.load(open(p))
recs = d if isinstance(d,list) else d.get('instances') or d.get('records') or []
print("records:",len(recs))
def pos(r):
    for k in ('pos','position','p'):
        if k in r and isinstance(r[k],(list,tuple)) and len(r[k])>=2: return r[k]
    return None
pts=[]
for r in recs:
    p=pos(r)
    if p and all(isinstance(v,(int,float)) for v in p[:3]): pts.append(p)
print("with pos:",len(pts))
if not pts: raise SystemExit("no positions")
xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; zs=[p[2] for p in pts]
print("x %.0f..%.0f  y %.0f..%.0f  z %.0f..%.0f"%(min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)))
W=H=1600
minx,maxx,miny,maxy=min(xs),max(xs),min(ys),max(ys)
sx=(W-40)/(maxx-minx); sy=(H-40)/(maxy-miny); s=min(sx,sy)
img=bytearray(W*H*3)
# dark background
for i in range(W*H): img[i*3]=8; img[i*3+1]=10; img[i*3+2]=16
import math
for (x,y,z) in pts:
    px=int(20+(x-minx)*s); py=int(20+(maxy-y)*s)
    if 0<=px<W and 0<=py<H:
        # colour by height: low=blue-grey, mid=green, high=bright
        t=min(1.0,max(0.0,(z+50)/250.0))
        r=int(40+215*t); g=int(90+120*(1-abs(t-0.5)*2)); b=int(200-150*t)
        o=(py*W+px)*3
        img[o]=max(img[o],r); img[o+1]=max(img[o+1],g); img[o+2]=max(img[o+2],b)
def chunk(t,data):
    c=t+data
    return struct.pack('>I',len(data))+c+struct.pack('>I',zlib.crc32(c)&0xffffffff)
raw=b''.join(b'\x00'+bytes(img[y*W*3:(y+1)*W*3]) for y in range(H))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b'')
open('work/world2/out/VICE_CITY_MAP.png','wb').write(png)
print("wrote work/world2/out/VICE_CITY_MAP.png",len(png),"bytes")
