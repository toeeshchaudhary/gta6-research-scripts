import numpy as np
from PIL import Image
im=Image.open("engine/shot.png").convert("RGB"); a=np.asarray(im,dtype=np.float32)
print("size",im.size,"mean",a.reshape(-1,3).mean(0).round(1),"std",a.reshape(-1,3).std(0).round(1))
# background is clear color 0.05,0.06,0.09 -> approx sRGB (0.26,0.29,0.35)*255? count near-clear pixels
bg=np.abs(a-np.array([15,17,23])).max(2)<12
print("bg-like pixels",bg.sum(),"of",bg.size,"frac",round(bg.mean(),3))
# center crop stats (object should be there)
c=a[300:420,560:720]
print("center mean",c.reshape(-1,3).mean(0).round(1),"std",c.reshape(-1,3).std(0).round(1))
print("unique colors",len(np.unique(a.reshape(-1,3).astype(np.uint8),axis=0)))
