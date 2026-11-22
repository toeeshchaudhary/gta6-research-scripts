import json, collections
d=json.load(open(r"work\world\world_scene.json"))
inst=d["instances"]
for t in ("0xd26a7425","0xb737b962"):
    hits=[i for i in inst if i["hash"]==t]
    print(t, len(hits))
    for h in hits[:8]: print("   ", h["resource"], h["pos"], h["rot"])
# resource 0xFE970B010 view
r=[i for i in inst if i["resource"]=="0xFE970B010"]
print("res 0xFE970B010 instances:", len(r))
pos=[i["pos"] for i in r]
import statistics
if pos:
    xs=[p[0] for p in pos]; ys=[p[1] for p in pos]; zs=[p[2] for p in pos]
    print("x",min(xs),max(xs));print("y",min(ys),max(ys));print("z",min(zs),max(zs))
    print("unique pos", len({tuple(p) for p in pos}))
