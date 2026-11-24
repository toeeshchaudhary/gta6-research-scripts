import json

scene = json.load(open(r'work/world/scene_streets.json'))
arch = json.load(open(r'work/draw/out/arch_model.json'))

by_hash = {}
for b in arch['bindings']:
    by_hash.setdefault(b['archetype_hash'].lower(), b)

for h, b in by_hash.items():
    inst = [i for i in scene['instances'] if i['hash'].lower() == h]
    if not inst:
        continue
    safe = b['name'].replace('/', '_').replace('\\', '_').strip('._') or h
    json.dump({'note': f'single archetype {h} {b["name"]}', 'instances': inst},
              open(rf'work/draw/out/verify_{safe}.json', 'w'), indent=1)
    print(h, b['name'], len(inst), b['obj_file'])
