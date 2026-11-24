import json, os, sys
sys.path.insert(0,'.')
import stitchlib as S
st=json.load(open('streams_meta.json'))
blocks=S.blocks()
def bo(off):
    for i,st0,ln in blocks:
        if st0<=off<st0+ln: return (i,st0,ln)
    return None
print("first 25 streams")
for s in st[:25]:
    b=bo(s['off'])
    print("  0x%08X end 0x%08X (align16 0x%08X) out %6d cons %6d mode %-9s blk %s" % (
        s['off'], s['end'], S.align16(s['end']), 0, s['cons'], s['mode'], b[:2] if b else None))
print()
print("blocks: first 12 / last 3")
for b in blocks[:12]: print("   ", b)
for b in blocks[-3:]: print("   ", b)
print("sum dataLen", sum(l for _,_,l in blocks), "region", S.REGION_END-S.REGION_START)
print()
import collections
print("stream offsets sorted deltas:", collections.Counter((b['off']-a['off'])//16 for a,b in zip(st,st[1:])).most_common(8))
print("min/max stream off: 0x%X 0x%X" % (st[0]['off'], st[-1]['off']))
