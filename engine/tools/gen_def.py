import re
lines=open("engine/vk_exports.txt", encoding="utf-8", errors="ignore").read().splitlines()
names=[]
for l in lines:
    m=re.search(r"\s(\d+)\s+[0-9A-F]+\s+[0-9A-F]+\s+(vk\w+)\s*$", l)
    if m: names.append(m.group(2))
print(len(names),"names")
with open("engine/vulkan-1.def","w",newline="\r\n") as f:
    f.write("LIBRARY vulkan-1.dll\nEXPORTS\n")
    for n in names: f.write("  "+n+"\n")
