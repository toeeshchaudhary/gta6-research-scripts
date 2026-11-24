import glob,json,os,collections,hashlib,re
idx=json.load(open(r's2_in\index.json',encoding='utf-8'))
h=collections.Counter(); keys=collections.Counter()
t=0
for e in idx:
    p=os.path.join(r's2_in',e['file'])
    b=open(p,'rb').read()
    h[hashlib.md5(b).hexdigest()]+=1
    keys[re.sub(r'^\d+_','',os.path.splitext(e['file'])[0])]+=1
    t+=1
print('files',t,'distinct dxbc hashes',len(h),'distinct stripped names',len(keys))
print('dup multiplicity',collections.Counter(h.values()).most_common(6))
print('name multiplicity',collections.Counter(keys.values()).most_common(6))
