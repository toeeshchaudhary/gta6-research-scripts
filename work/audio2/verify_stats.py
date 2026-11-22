import csv
rows=list(csv.DictReader(open(r'.\work\audio2\verify_samples\verify.csv',encoding='utf-8')))
d=[abs(float(r['deltaMs'])) for r in rows if r['deltaMs']]
print('n',len(rows),'pass',sum(1 for r in rows if r['pass_']=='True'),'fail',sum(1 for r in rows if r['pass_']!='True'))
print('exact matches',sum(1 for x in d if x==0),'max |delta| ms',max(d),'mean |delta| ms',round(sum(d)/len(d),3))
print('ffmpeg nonempty stderr',sum(1 for r in rows if r['stderr'].strip()))
print('nonzero exits',sum(1 for r in rows if r['ffmpegExit']!='0'))
op=[r for r in rows if r['codec']=='11']
print('opus',len(op),'dur range',min(float(r['declaredDuration']) for r in op),max(float(r['declaredDuration']) for r in op))
print('distinct new banks in sample',len(set(r['bank'] for r in rows)))
