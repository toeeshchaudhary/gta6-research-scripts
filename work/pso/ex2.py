import json
for line in open('work/pso/dump/script.jsonl',encoding='utf-8'):
    j=json.loads(line); p=j['Pipeline']
    if p.get('stateMask0')=='0x00000003':
        print(j['Source'].split('\\')[-1], p); break
