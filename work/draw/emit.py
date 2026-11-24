"""Bind extracted OBJ files to archetype hashes and resolve the street scene.

Input is the extractor manifest (offset -> obj file, only status ok rows) joined onto
bindings.json (hash -> name -> declaring resource). A binding is emitted only when
(a) joaat(name) == hash still holds and (b) the OBJ for that exact resource decoded.
"""
import json, os, collections

OUT = r'work/draw/out'
ARCHIVE = 'levels.rpf.part'

manifest = {}
for line in open(os.path.join(OUT, 'manifest.tsv'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.rstrip('\n').split('\t')
    if len(p) < 7 or p[3] != 'ok':
        continue
    try:
        off = int(p[0], 16)
    except ValueError:
        continue
    manifest[off] = {'name': p[1], 'hash': p[2].lower(), 'obj': p[6],
                     'verts': int(p[4]), 'tris': int(p[5])}
print('extracted ok models:', len(manifest))

bindings = json.load(open(r'work/arch/out/bindings.json'))['bindings']


def joaat(s):
    h = 0
    for c in s.lower():
        h = (h + ord(c)) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF


rows, by_hash, offset_used = [], {}, set()
for b in bindings:
    res = b.get('drawable_resource')
    if not res:
        continue
    off = int(res, 16)
    m = manifest.get(off)
    if not m:
        continue
    h = b['archetype_hash'].lower()
    if joaat(b['name']) != int(h, 16):
        continue
    entry = {
        'archetype_hash': h,
        'name': b['name'],
        'resource_offset': res,
        'obj_file': 'work/draw/out/models/' + m['obj'],
        'verts': m['verts'],
        'tris': m['tris'],
        'drawable_type': b.get('drawable_type') or '',
    }
    rows.append(entry)
    by_hash.setdefault(h, entry)
    offset_used.add(off)

rows.sort(key=lambda r: r['archetype_hash'])
with open(os.path.join(OUT, 'arch_model.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump({'archive': ARCHIVE, 'count': len(rows), 'bindings': rows}, f, indent=1)
print('arch_model.json bindings:', len(rows), 'distinct hashes:', len(by_hash),
      'distinct resources used:', len(offset_used))

scene = json.load(open(r'work/world/scene_streets.json'))
cnt = collections.Counter(i['hash'].lower() for i in scene['instances'])
resolved_h = [h for h in cnt if h in by_hash]
covered = sum(cnt[h] for h in resolved_h)
out_inst = []
for i in scene['instances']:
    h = i['hash'].lower()
    b = by_hash.get(h)
    o = dict(i)
    o['model'] = b['obj_file'] if b else None
    o['model_name'] = b['name'] if b else None
    o['verified'] = bool(b)
    out_inst.append(o)
scene_out = dict(scene)
scene_out['instances'] = out_inst
scene_out['resolution'] = {
    'instances': len(out_inst),
    'distinct_hashes': len(cnt),
    'hashes_with_model': len(resolved_h),
    'instances_with_model': covered,
    'hash_rate': round(100.0 * len(resolved_h) / len(cnt), 2),
    'instance_rate': round(100.0 * covered / len(out_inst), 3),
}
json.dump(scene_out, open(os.path.join(OUT, 'scene_streets_models.json'), 'w', encoding='utf-8', newline='\n'), indent=1)
print('scene instances with model:', covered, '/', len(out_inst),
      f'({100.0 * covered / len(out_inst):.3f}%) hashes {len(resolved_h)}/{len(cnt)}')

# also report the same over the whole world scene, for context
world = json.load(open(r'work/world/world_scene.json'))
wcnt = collections.Counter(i['hash'].lower() for i in world['instances'])
wh = [h for h in wcnt if h in by_hash]
print('world instances with model:', sum(wcnt[h] for h in wh), '/', len(world['instances']),
      'hashes', len(wh), '/', len(wcnt))
