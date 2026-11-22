import json,os,statistics
OUT=r'.\work\mission\out'
n=0; trapix=0; fs=[]
for fn in os.listdir(OUT):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    d=json.load(open(os.path.join(OUT,fn),encoding='utf-8')); n+=1
    if d['header']['trailing']>0: trapix+=1
    for c in d['chunks']:
        if 'float_share' in c: fs.append(c['float_share'])
print('files',n,'with trailing bytes',trapix,'%.1f%%'%(100*trapix/n))
print('blob chunks',len(fs),'mean float_share %.3f'%statistics.mean(fs))
d=json.load(open(os.path.join(OUT,'g1798_04677000.json')))
print([c['tag'] for c in d['chunks']])
