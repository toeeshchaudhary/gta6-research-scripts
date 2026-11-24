import sys, json
sys.path.insert(0,'.')
import stitchlib as S
D=S.data()
for off in (0x4D3B0, 0x1A7590, 0x228260, 0x36CBA0, 0x99EE00, 0x3056BF0):
    print("=== stream 0x%08X : 48 bytes BEFORE start ===" % off)
    print(S.hexdump(D, off-48, 16, 48))
    st=[s for s in json.load(open('streams_meta.json')) if s['off']==off]
    if st:
        e=st[0]['end']
        print("--- end 0x%08X, 48 bytes AFTER ---" % e)
        print(S.hexdump(D, e, 16, 48))
    print()
