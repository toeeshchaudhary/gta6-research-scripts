import numpy as np
from PIL import Image
a=np.asarray(Image.open("engine/shot.png").convert("L").resize((100,40)),dtype=np.float32)
bg=np.abs(np.asarray(Image.open("engine/shot.png").convert("RGB").resize((100,40)),dtype=np.float32)-np.array([15,17,23])).max(2)<18
chars=" .:-=+*#%@"
for y in range(40):
    row=""
    for x in range(100):
        if bg[y,x]: row+=" "
        else:
            v=a[y,x]/255.0
            row+=chars[min(9,int(v*10))]
    print(row)
