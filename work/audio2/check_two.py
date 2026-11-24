import json,csv
new=json.load(open(r'.\work\audio2\audio_index.json',encoding='utf-8'))
old=json.load(open(r'.\work\audio\audio_index.json',encoding='utf-8'))
oo={b['offset'] for b in old['banks']}
fresh=[b for b in new['banks'] if b['offset'] not in oo]
holes=[(int(r['Start']),int(r['Gap'])) for r in csv.DictReader(open(r'.\work\audio\hole_ranges.csv'))]
alloc=[(int(r['Offset']),int(r['Length'])) for r in csv.DictReader(open(r'.\work\audio\allocated_ranges.csv'))]
alloc.sort(); holes.sort()
def inr(rng,off):
    for o,l in rng:
        if o<=off<o+l: return (o,l)
    return None
out=[]
for b in fresh:
    off=b['offset']
    if not inr(holes,off):
        # distance to end of the allocated range that contains it, and to the next hole
        a=inr(alloc,off)
        nxt=min([h for h in holes if h[0]>off], default=None)
        out.append((off,b['size'],a, None if not a else a[0]+a[1]-off, nxt))
print('banks not starting in a T+0 hole:',len(out))
for o in out: print('  off %X size %d alloc %s bytes_to_alloc_end %s next_hole %s'%(o[0],o[1],o[2],o[3],o[4]))
