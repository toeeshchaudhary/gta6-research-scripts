import re, os, sys
from pathlib import Path
rows=[]
for p in Path(r"./work/assets").rglob("*.obj"):
    nv=0; nf=0; nv_used=set()
    with p.open("r", errors="ignore") as f:
        for line in f:
            if line[:2]=="v ": nv+=1
            elif line[:2]=="f ":
                nf+=1
                for tok in line[2:].split():
                    nv_used.add(tok.split("/")[0])
    rows.append((nf,nv,len(nv_used),p.stat().st_size,p))
rows.sort(reverse=True)
print("top by triangles:")
for r in rows[:15]:
    print(f"  tris={r[0]:7d} v={r[1]:7d} used={r[2]:7d} {r[4].name}")
print("total tris:", sum(r[0] for r in rows))
print("models with >100k tris:", sum(1 for r in rows if r[0]>100000))
