import json, collections
d=json.load(open(r"work\world\world_scene.json"))
print("counts", d["counts"])
inst=d["instances"]
print("n inst", len(inst))
print("keys", list(inst[0].keys()))
print(inst[0])
print("resources keys:", list(d["resources"].keys())[:5] if isinstance(d["resources"],dict) else type(d["resources"]))
