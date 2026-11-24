import json,os
m=json.load(open('resources/manifest.json'))
print("files",len(m),"bytes",sum(x['size'] for x in m),"multi",sum(1 for x in m if x['n_chunks']>1))
for x in sorted(m,key=lambda x:-x['size']):
    print("| %s | %d | %d | %d | %d | %s | %s |" % (x['resource'],x['size'],x['n_chunks'],x['records_0x88'],x['pointers'],x['targets_inside'],x['array_score']))
