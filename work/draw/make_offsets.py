import json, collections

b = json.load(open(r'work/arch/out/bindings.json'))
street = json.load(open(r'work/world/scene_streets.json'))
world = json.load(open(r'work/world/world_scene.json'))

street_h = collections.Counter(i['hash'].lower() for i in street['instances'])
world_h = collections.Counter(i['hash'].lower() for i in world['instances'])

rows, seen = [], set()
for r in b['bindings']:
    res = r.get('drawable_resource')
    if not res:
        continue
    off = res.lower()
    if off in seen:
        continue
    seen.add(off)
    h = r['archetype_hash'].lower()
    pri = 0 if h in street_h else (1 if h in world_h else 2)
    rows.append((pri, off, r['name'], h))
rows.sort(key=lambda x: (x[0], x[1]))
with open(r'work/draw/offsets.tsv', 'w', encoding='utf-8', newline='\n') as f:
    f.write('# offset\tname\thash\n')
    for pri, off, name, h in rows:
        f.write(f'{off}\t{name}\t{h}\n')
print('offsets', len(rows), 'street-bound', sum(1 for r in rows if r[0] == 0))
