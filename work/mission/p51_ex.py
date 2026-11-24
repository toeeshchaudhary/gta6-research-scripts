import json
d=json.load(open(r'.\work\mission\out\g1730_045AE000.json'))
print('header',d['header'])
for ch in d['chunks'][:8]:
    print(ch['tag'],ch['role'],ch['size'],ch['validity'])
ch=[c for c in d['chunks'] if c['tag']=='00000109'][0]
for r in ch['records'][:3]+[x for x in ch['records'] if x['key']=='6a131547'][:2]:
    print(json.dumps(r)[:400])
