"""M4: emit the 1,323 bound world instances of world_scene.json as a scene file
with their extracted transforms, for an honest "as extracted" render."""
import json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
arch = {}
for r in json.load(open(os.path.join(ROOT, 'work/draw/out/arch_model.json'), encoding='utf-8'))['bindings']:
    arch.setdefault(r['archetype_hash'].lower(), r)
sc = json.load(open(os.path.join(ROOT, 'work/world/world_scene.json'), encoding='utf-8'))['instances']
out = []
for i in sc:
    r = arch.get(i['hash'].lower())
    if not r:
        continue
    out.append({'hash': i['hash'], 'model': r['obj_file'], 'name': r['name'], 'pos': i['pos'],
                'rot': i['rot'], 'scale': i['scale'], 'tag': 'bld'})
json.dump({'note': 'the 1,323 bound world instances exactly as extracted', 'instances': out},
          open(os.path.join(ROOT, 'engine/out/m4_bound_asis.json'), 'w'), indent=1)
print('wrote engine/out/m4_bound_asis.json', len(out))
