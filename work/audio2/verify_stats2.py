import csv
rows=list(csv.DictReader(open(r'.\work\audio2\verify_samples\verify.csv',encoding='utf-8')))
for r in rows:
    if r['deltaMs'] and abs(float(r['deltaMs']))>0:
        print(r['i'],r['bank'],'codec',r['codec'],'sr',r['sr'],'decl',r['declaredFrames'],'dec',r['decodedFrames'],'dms',r['deltaMs'],r['note'])
print('codec counts',{c:sum(1 for r in rows if r['codec']==c) for c in set(r['codec'] for r in rows)})
