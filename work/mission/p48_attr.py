import json,os,sys,collections
sys.path.insert(0,r'.\work\mission')
import lib_min as L
OUT=r'.\work\mission\out'
src=L.build_dicts(); dic,origin=L.merged(src)
attr=collections.Counter(); key=collections.Counter()
n=0; withattr=0; resattr=0; reskey=0; withvals=0
for fn in os.listdir(OUT):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    d=json.load(open(os.path.join(OUT,fn),encoding='utf-8'))
    for ch in d['chunks']:
        for r in ch.get('records',[]):
            n+=1
            if 'values' in r: withvals+=1
            a=int(r['attr'],16) if r['attr'] else 0
            k=int(r['key'],16)
            if a:
                withattr+=1; attr[a]+=1
                if a in dic: resattr+=1
            if k in dic: reskey+=1; key[k]+=1
print('records',n,'with pool values',withvals)
print('records with attr',withattr,'resolved attr',resattr,'(%.1f%%)'%(100*resattr/max(1,withattr)))
print('resolved keys',reskey)
print()
print('top attr names:')
for h,c in attr.most_common(25):
    print(' %08x %5d %s  [%s]'%(h,c,dic.get(h,'-'),origin.get(h,'')))
print()
print('top key names:')
for h,c in key.most_common(25):
    print(' %08x %5d %s  [%s]'%(h,c,dic.get(h,'-'),origin.get(h,'')))
