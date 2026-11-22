import json,os,sys,collections
sys.path.insert(0,r'.\work\mission')
import lib_min as L
OUT=r'.\work\mission\out'
src=L.build_dicts(); dic,origin=L.merged(src)
per=collections.defaultdict(lambda: {'n':0,'attrres':0,'keyres':0,'attr':collections.Counter(),'key':collections.Counter(),'files':set()})
for fn in os.listdir(OUT):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    d=json.load(open(os.path.join(OUT,fn),encoding='utf-8'))
    for ch in d['chunks']:
        rs=ch.get('records')
        if not rs: continue
        t=ch['tag']; e=per[t]; e['files'].add(fn); e['n']+=len(rs)
        for r in rs:
            a=int(r['attr'],16) if r['attr'] else 0
            k=int(r['key'],16)
            if a in dic: e['attrres']+=1; e['attr'][dic[a]]+=1
            if k in dic: e['keyres']+=1; e['key'][dic[k]]+=1
rows=sorted(per.items(), key=lambda kv:-kv[1]['n'])
for t,e in rows[:14]:
    print('tag %s recs=%d files=%d keyres=%d attrres=%d'%(t,e['n'],len(e['files']),e['keyres'],e['attrres']))
    print('   keys:',', '.join('%s(%d)'%(n,c) for n,c in e['key'].most_common(6)))
    print('   attrs:',', '.join('%s(%d)'%(n,c) for n,c in e['attr'].most_common(6)))
