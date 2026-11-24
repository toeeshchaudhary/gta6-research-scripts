import json,collections
# checksum match rate + counts for the report
for f in ('work/pso/dump/script.jsonl','work/pso/dump/story.jsonl'):
    n=0; ok=0; lh=0; enums=0; blocks=0; shr=0
    for line in open(f,encoding='utf-8'):
        j=json.loads(line); n+=1
        if j['ChecksumStored']==j['ChecksumComputed']: ok+=1
        if j['LsnsHeaderWellFormed']: lh+=1
        enums+=len(j['Enums']); blocks+=len(j['Blocks'])
    print(f,"records",n,"checksumMatch",ok,"lsnsWellFormed",lh,"enumTables",enums,"blocks",blocks)
