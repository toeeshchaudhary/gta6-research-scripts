import struct
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
# check candidate cell strides for pool 0x10a
start=11696; size=22080; end=start+size
for stride in (16,20,24,32,40,48,64):
    for hdr in (0,8,12,16):
        ok=0;tot=0
        i=start+hdr
        while i+stride<=end:
            tot+=1
            f=struct.unpack_from('<%df'%(stride//4),b,i)
            # sanity: first float in [-10000,10000] and not 0, finite
            v=f[0]
            if abs(v)>1e-3 and 1e-9<abs(v)<1e6: ok+=1
            i+=stride
        print('stride',stride,'hdr',hdr,'ratio %.2f'%(ok/tot),tot)
