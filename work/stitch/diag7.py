import json, os, sys
sys.path.insert(0,'.')
import stitchlib as S
meta=sorted(json.load(open('streams_meta.json')), key=lambda s:s['off'])
gaps=[b['off']-S.align16(a['end']) for a,b in zip(meta,meta[1:])]
print("pairs",len(gaps),"min gap",min(gaps),"max",max(gaps),"gaps==0",sum(1 for g in gaps if g==0))
print("gaps<16:",sum(1 for g in gaps if g<16),"gaps<256:",sum(1 for g in gaps if g<256))
print("streams",len(meta),"bytes",sum(len(open(os.path.join(S.ROOT,'work\\codec\\full\\exact','exact_%08X.bin'%s['off'])).read()) if os.path.exists(os.path.join(S.ROOT,'work\\codec\\full\\exact','exact_%08X.bin'%s['off'])) else 1 for s in meta))
print("first/last stream off: 0x%X 0x%X"%(meta[0]['off'],meta[-1]['off']))
# distinct stream sizes
import collections
print("modes",collections.Counter(s['mode'] for s in meta))
# how many streams are page+16 payloads
print("off%4096==16:",sum(1 for s in meta if s['off']%4096==16),"off%16:",collections.Counter(s['off']%16 for s in meta).most_common(4))
