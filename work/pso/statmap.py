import json,glob,collections
c=collections.Counter(); m=collections.Counter(); b=collections.Counter(); d=collections.Counter(); kind=collections.Counter()
for f in ('work/pso/dump/script.jsonl','work/pso/dump/story.jsonl'):
    for line in open(f,encoding='utf-8'):
        j=json.loads(line)
        p=j['Pipeline']; cl=j['Classification']
        kind[p.get('kind')]+=1
        m[p.get('stateMask0')]+=1; b[p.get('stateByte0')]+=1; d[cl.get('drawType')]+=1
print("kind",kind.most_common())
print("mask0 top",m.most_common(8))
print("byte0 top",b.most_common(8))
print("runtime",d.most_common())
print("hashes per file avg", sum(int(json.loads(l)['Pipeline'].get('hashCount',0)) for l in open('work/pso/dump/script.jsonl',encoding='utf-8'))/1009)
