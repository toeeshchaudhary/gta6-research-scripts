import json, collections

world = json.load(open(r'work/world/scene_world.json'))['instances']
arch = {b['archetype_hash'].lower(): b for b in json.load(open(r'work/draw/out/arch_model.json'))['bindings']}

bound = [i for i in world if i['hash'].lower() in arch]
print('bound world-space instances', len(bound), 'of', len(world))

# densest 150-unit x bin, then prefer bins that also have many distinct (building-like) hashes
bins = collections.defaultdict(list)
for i in bound:
    bins[int(i['pos'][0] // 150)].append(i)
scored = sorted(bins.items(), key=lambda kv: (-len({x['hash'] for x in kv[1]}), -len(kv[1])))
for k, v in scored[:5]:
    print('bin', k * 150, 'instances', len(v), 'hashes', len({x['hash'] for x in v}))
best = [k for k, _ in scored][:1]
key = best[0]
sel = bins[key]
by_h = collections.Counter(i['hash'].lower() for i in sel)
print('distinct', len(by_h), 'sample names', [arch[h]['name'] for h in list(by_h)[:10]])
json.dump({'note': 'world-space block around x=%d, bound archetypes only' % (key * 150),
           'instances': sel[:1500]},
          open(r'work/draw/out/verify_world_block.json', 'w'), indent=1)
