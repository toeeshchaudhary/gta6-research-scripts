import numpy as np
from PIL import Image
for f in ["shot_model2.png","shot_bc6h.png","shot_stress.png"]:
    a=np.asarray(Image.open("engine/"+f).convert("RGB"),dtype=np.float32)
    bg=np.abs(a-np.array([15,17,23])).max(2)<18
    print(f,"mean",a.reshape(-1,3).mean(0).round(1),"std",a.reshape(-1,3).std(0).round(1),"fg%",round(100*(1-bg.mean()),2),"colors",len(np.unique(a.astype(np.uint8).reshape(-1,3),axis=0)))
