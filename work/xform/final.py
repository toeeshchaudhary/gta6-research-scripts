import json, collections
d=json.load(open(r"work\xform\out\scene_S.json"))
recs=d["instances"]
hs=collections.Counter(r["hash"] for r in recs)
names={}
for line in open(r"work\arch\dict\d3_names.tsv",encoding="utf-8",errors="replace"):
    p=line.rstrip("\n").split("\t")
    if len(p)>=2:
        try: names[int(p[0],16)]=p[1]
        except: pass
res=[(h,n) for h,n in hs.items() if int(h,16) in names]
print("distinct archetype hashes:", len(hs))
print("resolved via d3_names:", len(res), "covering", sum(hs[h] for h,_ in res), "instances")
print("top hashes:", [(h,n) for h,n in hs.most_common(8)])
print("sample resolved:", [(h,names[int(h,16)],n) for h,n in res[:10]])
