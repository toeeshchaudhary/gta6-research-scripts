import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
pairs=[('010d',38032,224,34000,4032),('010f',51984,224,52208,1344),('0111',53552,224,53776,30912),('0113',84688,224,84912,608)]
for name,to,tz,do,dz in pairs:
    print('==',name,'data',do)
    recs=[struct.unpack_from('<8I',b,to+16+32*k) for k in range(6)]
    for r in recs[:2]:
        cnt=r[4]&0xffff; off=r[4]>>16
        print('  rec cnt=%d off=%d'%(cnt,off))
        for unit,tag in ((4,'dword'),(1,'byte')):
            o=do+off*unit
            print('    %s @%d: %s'%(tag,o,b[o:o+cnt*4].hex(' ')))
    print()
