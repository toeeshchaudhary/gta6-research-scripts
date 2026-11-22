p="ENGINE.md"
s=open(p,encoding="utf-8").read()
s=s.replace("![first frame](shot.png)","![first frame](engine/shot.png)")
s=s.replace("`shots\\shot_model2.png`","`engine\\shots\\shot_model2.png`")
s=s.replace("`shots\\shot_bc6h.png`","`engine\\shots\\shot_bc6h.png`")
s=s.replace("`shot.png` ? frame 220","`engine\\shot.png` ? frame 220")
open(p,"w",encoding="utf-8").write(s)
print("ok")
