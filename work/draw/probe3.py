import json, collections
b=json.load(open(r'work/arch/out/bindings.json'))
print(json.dumps(b['stats'], indent=1))
offs=collections.Counter()
for r in b['bindings']:
    d=r.get('drawable_resource')
    if d: offs[d]+=1
print('bindings',len(b['bindings']),'distinct drawable resources',len(offs))
print(list(offs.items())[:5])
# how many distinct hashes with drawable
print('with drawable', sum(1 for r in b['bindings'] if r.get('drawable_resource')))
# types
print(collections.Counter(r.get('drawable_type') for r in b['bindings']))
