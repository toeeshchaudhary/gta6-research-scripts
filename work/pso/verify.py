import json,collections
c=collections.Counter(); ex=[]
blocks=0; mism=0
for line in open('work/pso/dump/script.jsonl',encoding='utf-8'):
    j=json.loads(line); p=j['Pipeline']; cl=j['Classification']
    c[(p.get('stateMask0'),p.get('stateByte0'),cl.get('drawType'))]+=1
    if p.get('stateByte0') not in (None,'0'): ex.append((j['Source'].split('\\')[-1],p.get('stateMask0'),p.get('stateMask1'),p.get('stateMask2'),p.get('stateByte0')))
    for b in j['Blocks']:
        blocks+=1
        if b['StructLength'] and b['BlockLength']%b['StructLength']: mism+=1
print("mask0=0xC090AFAD & byte0=0 :", sum(v for (m,b,d),v in c.items() if m=='0xC090AFAD' and b=='0'))
print("byte0 non-zero files:",ex)
print("blocks",blocks,"len%structLen!=0",mism)
print("top combos:",c.most_common(6))
