import json
d=json.load(open(r'.\work\mission\out\_analysis.json'))
for k in ('files','files_with_records','total_records','roles','distinct_record_hashes','resolved_record_hashes','resolved_record_rate_pct'):
    print(k,d[k])
print('top:',[(x['hash'],x['count']) for x in d['top_unresolved_identifier']])
