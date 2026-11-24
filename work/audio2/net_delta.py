import json
new=json.load(open(r'.\work\audio2\audio_index.json',encoding='utf-8'))
old=json.load(open(r'.\work\audio\audio_index.json',encoding='utf-8'))
nb={b['offset']:b for b in new['banks']}; ob={b['offset']:b for b in old['banks']}
common=set(ob)&set(nb)
ds=sum(len(nb[o]['streams'])-len(ob[o]['streams']) for o in common)
dt=sum(sum(s['dur'] for s in nb[o]['streams'])-sum(s['dur'] for s in ob[o]['streams']) for o in common)
dec=[o for o in common if len(nb[o]['streams'])<len(ob[o]['streams'])]
print('common banks',len(common),'stream delta',ds,'seconds delta',round(dt,1),'banks w/ fewer streams',len(dec))
print('shrunk stream total',sum(len(ob[o]['streams'])-len(nb[o]['streams']) for o in dec))
print('total delta streams',new['streamCount']-old['streamCount'])
ts=sum(s['dur'] for b in new['banks'] for s in b['streams']); to=sum(s['dur'] for b in old['banks'] for s in b['streams'])
print('hours new %.2f old %.2f delta %.2f'%(ts/3600,to/3600,(ts-to)/3600))
ns=sum(1 for b in new['banks'] for s in b['streams'] if s['codec']==11 and not s['streamed'])
print('non-streamed opus',ns,'streamed',sum(1 for b in new['banks'] for s in b['streams'] if s['streamed']))
