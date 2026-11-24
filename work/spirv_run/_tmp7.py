import json,collections
rows=[json.loads(l) for l in open(r'logs_cs\rows.part0.jsonl',encoding='utf-8') if l.strip()]
print(len(rows),'val_ok',sum(r['val_ok'] for r in rows),'spirv',sum(r['spirv_ok'] for r in rows))
print(collections.Counter((r['error'] or 'OK')[:70] for r in rows).most_common(8))
print('mean insns',sum(r['insns'] for r in rows)/len(rows))
print('largest', sorted(((r['insns'],r['name']) for r in rows),reverse=True)[:3])
