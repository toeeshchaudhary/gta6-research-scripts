import json
d=json.load(open(r'.\work\mission\out\_per_file.json'))
d.sort(key=lambda x:-x['records'])
print('top record files:')
for x in d[:12]: print(x['file'],x['records'],x['missions'],x['named_keys'][:4])
print()
print('files with mission keys:',[x['file'] for x in d if x['missions']])
