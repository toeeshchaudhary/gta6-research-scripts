import sys, numpy as np
from PIL import Image
p = sys.argv[1]
W = int(sys.argv[2]) if len(sys.argv) > 2 else 160
H = int(sys.argv[3]) if len(sys.argv) > 3 else 60
im = Image.open(p).convert("RGB")
sm = np.asarray(im.resize((W, H)), dtype=np.float32)
a = np.asarray(im.convert("L").resize((W, H)), dtype=np.float32)
# sky colour of the current clear (0.42,0.56,0.76) and the old dark clear
sky = np.array([107, 143, 194], dtype=np.float32)
dark = np.array([13, 15, 23], dtype=np.float32)
issky = np.abs(sm - sky).max(2) < 10
isdark = np.abs(sm - dark).max(2) < 10
chars = " .:-=+*#%@"
out = []
for y in range(H):
    row = []
    for x in range(W):
        if issky[y, x]:
            row.append('~')
        elif isdark[y, x]:
            row.append(' ')
        else:
            row.append(chars[min(9, int(a[y, x] / 255 * 10))])
    out.append("".join(row))
print("\n".join(out))
print("coverage: %.2f%% of pixels differ from both clears" % (100 * (~issky & ~isdark).mean()))
