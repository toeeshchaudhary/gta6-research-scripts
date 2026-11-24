import json,re,sys
p=sys.argv[1]
arch=json.load(open(r"../draw/out/arch_model.json"))
bh={b["archetype_hash"].lower() for b in arch["bindings"]}
cla={"M":[0,0],"S":[0,0]}; named={"M":0,"S":0}; tot={"M":0,"S":0}
rx=re.compile(rb'"hash":"(0x[0-9a-f]{8})".*?"class":"([MS])"')
data=open(p,"rb").read()
for m in rx.finditer(data):
    cl=m.group(2).decode(); h=m.group(1).decode(); tot[cl]+=1
    if h in bh: cla[cl][0]+=1
rep={"totals":tot,"bound":{k:v[0] for k,v in cla.items()},"bind_rate":{k:(v[0]/tot[k] if tot[k] else 0) for k,v in cla.items()}}
json.dump(rep,open("out/bind_by_class.json","w"),indent=1); print(json.dumps(rep,indent=1))
