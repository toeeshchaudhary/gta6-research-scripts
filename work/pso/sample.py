import json,collections,random
out=[]; kinds=collections.Counter()
for line in open('work/pso/dump/script.jsonl',encoding='utf-8'):
    j=json.loads(line); p=j['Pipeline']
    blocks=[]
    for b in j['Blocks']:
        it=[]
        for row in b['Items'][:2]:
            it.append([{ 'type':hex(f['Type']),'off':f['Offset'],'size':f['Size'],'ref':hex(f['Ref']) if f['Ref'] else 0,'v':(f['ValueText'][:40] if f['ValueText'] else None)} for f in row])
        blocks.append({'structHash':hex(b['StructHash']),'structLength':b['StructLength'],'blockLength':b['BlockLength'],'items':b['ItemCount'],'sampleItems':it})
    out.append({'src':j['Source'].split('\\')[-1],'size':j['Size'],'psinU0':j['PsinU0'],'root':hex(j['RootStruct']),
                'lsnsMethod':j['LsnsMethod'],'lsnsHeaderWellFormed':j['LsnsHeaderWellFormed'],
                'checksumStored':hex(j['ChecksumStored']),'checksumComputed':hex(j['ChecksumComputed']),
                'pipeline':p,'classification':j['Classification'],'blocks':blocks,'warnings':j['Warnings']})
random.seed(7); random.shuffle(out)
sel=out[:400]
json.dump({'note':'slim dump: 400 of 1009 script-class pipelines. Full data in script.jsonl / story.jsonl. Every value is INFERRED-BY-SHAPE unless labelled verified.','count':len(sel),'pipelines':sel}, open('work/pso/dump/pipelines.sample.json','w',encoding='utf-8'), indent=1)
print("wrote",len(sel))
