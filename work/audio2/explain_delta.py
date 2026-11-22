import json,sys
new=json.load(open(r'.\work\audio2\audio_index.json',encoding='utf-8'))
old=json.load(open(r'.\work\audio\audio_index.json',encoding='utf-8'))
nb={b['offset']:b for b in new['banks']}
ob={b['offset']:b for b in old['banks']}
holed=[b for b in old['banks'] if (b['holeBytes'] or 0)>0]
full=[b for b in old['banks'] if b['holeBytes'] and b['holeBytes']>=b['size']]
grown=[]
for b in holed:
    n=nb.get(b['offset'])
    if n and len(n['streams'])!=len(b['streams']):
        grown.append((b['offset'],len(b['streams']),len(n['streams']),b['holeBytes'],b['size']))
print('old banks with any hole',len(holed),'fully holed',len(full))
print('of those, banks whose stream count changed',len(grown))
print('extra streams from those banks',sum(g[2]-g[1] for g in grown))
print('extra seconds from those banks',
      round(sum(sum(s['dur'] for s in nb[g[0]]['streams'])-sum(s['dur'] for s in ob[g[0]]['streams']) for g in grown),1))
for g in sorted(grown,key=lambda x:-(x[2]-x[1]))[:5]:
    print('  off %X old %d new %d hole %d/%d'%(g[0],g[1],g[2],g[3],g[4]))
print('new banks streams/seconds', sum(len(b['streams']) for o,b in nb.items() if o not in ob),
      round(sum(s['dur'] for o,b in nb.items() if o not in ob for s in b['streams']),1))
print('BANKENS/streams identical?', sorted(ob)==sorted(nb))
