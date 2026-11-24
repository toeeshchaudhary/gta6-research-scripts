import json,zlib,struct
d=json.load(open('work/world2/out/scene_world_full.json'))
recs = d if isinstance(d,list) else d.get('instances') or d.get('records') or []
xs=[];ys=[];zs=[]
for r in recs:
    p=r.get('pos') or r.get('position')
    if p: xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
def pct(a,q):
    b=sorted(a); return b[int(q*(len(b)-1))]
x0,x1=pct(xs,0.02),pct(xs,0.98); y0,y1=pct(ys,0.02),pct(ys,0.98)
print("core extent x %.0f..%.0f  y %.0f..%.0f"%(x0,x1,y0,y1))
W=H=1800
s=min((W-40)/(x1-x0),(H-40)/(y1-y0))
img=bytearray(W*H*3)
for i in range(W*H): img[i*3],img[i*3+1],img[i*3+2]=6,8,14
zmin,zmax=pct(zs,0.02),pct(zs,0.98)
n=0
for x,y,z in zip(xs,ys,zs):
    if not (x0<=x<=x1 and y0<=y<=y1): continue
    px=int(20+(x-x0)*s); py=int(20+(y1-y)*s)
    t=max(0.0,min(1.0,(z-zmin)/max(1,zmax-zmin)))
    r=int(30+225*t); g=int(120+100*(1-abs(t-0.6)/0.6) if t<1.2 else 0); b=int(230-170*t)
    for dy in (0,1):
        for dx in (0,1):
            X,Y=px+dx,py+dy
            if 0<=X<W and 0<=Y<H:
                o=(Y*W+X)*3; img[o]=max(img[o],r); img[o+1]=max(img[o+1],g); img[o+2]=max(img[o+2],b)
    n+=1
print("plotted",n)
def chunk(t,data):
    c=t+data; return struct.pack('>I',len(data))+c+struct.pack('>I',zlib.crc32(c)&0xffffffff)
raw=b''.join(b'\x00'+bytes(img[y*W*3:(y+1)*W*3]) for y in range(H))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
open('work/world2/out/VICE_CITY_CORE.png','wb').write(png)
print("wrote VICE_CITY_CORE.png",len(png))
