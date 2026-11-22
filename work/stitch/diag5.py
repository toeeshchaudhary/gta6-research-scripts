import sys, json
sys.path.insert(0,'.')
import stitchlib as S
D=S.data()
meta={s['off']:s for s in json.load(open('streams_meta.json'))}
for off in (0x4D3B0, 0x1A7590, 0x99EE00, 0x3056BF0):
    print("=== stream 0x%08X : 64 bytes BEFORE ===" % off)
    print(S.dump_at(D, off-64, 64))
    e=meta[off]['end']
    print("--- end 0x%08X : 64 bytes AFTER ---" % e)
    print(S.dump_at(D, e, 64))
    print()
