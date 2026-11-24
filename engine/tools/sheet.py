import glob
from PIL import Image, ImageDraw
fs=sorted(glob.glob("./engine/_texprev/*.png"))
cols=6; rows=(len(fs)+cols-1)//cols
sheet=Image.new("RGB",(cols*270,rows*300),(30,30,30))
d=ImageDraw.Draw(sheet)
for i,f in enumerate(fs):
    im=Image.open(f)
    x=(i%cols)*270; y=(i//cols)*300
    sheet.paste(im,(x+5,y+5))
    d.text((x+5,y+265), f.split("\\")[-1][:44], fill=(255,255,255))
sheet.save("./engine/_texprev/sheet.png")
print("sheet", sheet.size, len(fs))
