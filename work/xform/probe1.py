import json, struct, sys, collections
def joaat(s):
    h=0
    for ch in s.lower():
        h=(h+ord(ch))&0xFFFFFFFF
        h=(h+(h<<10))&0xFFFFFFFF
        h^=h>>6
    h=(h+(h<<3))&0xFFFFFFFF
    h^=h>>11
    return (h+(h<<15))&0xFFFFFFFF

names=["des_bhf_tower_02_collapse_06","prop_am_fencetech_rail_09_3m_nc"]
targets={joaat(n):n for n in names}
print({hex(k):v for k,v in targets.items()})

print("loading json...")
d=json.load(open(r"work\world\world_scene.json"))
print(type(d), (list(d.keys())[:8] if isinstance(d,dict) else len(d)))
