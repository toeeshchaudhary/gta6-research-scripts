import json,collections
tot=0; mism=0
for f in ('work/pso/dump/script.jsonl','work/pso/dump/story.jsonl'):
    for line in open(f,encoding='utf-8'):
        j=json.loads(line)
        for b in j['Blocks']:
            tot+=1
            if b['StructLength'] and b['BlockLength']%b['StructLength']: mism+=1
print("blocks",tot,"mismatch",mism)
for line in open('work/pso/dump/script.jsonl',encoding='utf-8'):
    j=json.loads(line)
    if 'p0092_00118000' in j['Source']:
        print(j['Source']); print(j['Pipeline']); print(j['Classification'])
