import sys, numpy as np
from PIL import Image
p=sys.argv[1]
im=Image.open(p).convert("RGB")
sm=np.asarray(im.resize((100,40)),dtype=np.float32)
a=np.asarray(im.convert("L").resize((100,40)),dtype=np.float32)
bg=np.abs(sm-np.array([15,17,23])).max(2)<18
chars=" .:-=+*#%@"
for y in range(40):
    print("".join(" " if bg[y,x] else chars[min(9,int(a[y,x]/255*10))] for x in range(100)))
