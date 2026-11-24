import json
d=json.load(open(r'.\work\mission\out\_analysis.json'))
for x in d['top_unresolved_identifier']: print(x['hash'],x['count'])
print('---')
for k in ('files','files_with_records','total_records','distinct_record_hashes','resolved_record_hashes','resolved_record_rate_pct'):
    print(k,d[k])
