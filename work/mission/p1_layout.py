import struct,sys
p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
print('len',len(b),'magic',b[:4])
print('u32@4',hex(struct.unpack_from('<I',b,4)[0]))
print('u32@8',hex(struct.unpack_from('<I',b,8)[0]))
print('u32@12',hex(struct.unpack_from('<I',b,12)[0]))
n=(len(b)-8)//16
print('n_desc if hdr8',n,'rem',(len(b)-8)%16)
# walk descriptors from 8
tot=0;tags={}
i=8;cnt=0
while i+16<=len(b):
    t,s=struct.unpack_from('<II',b,i)
    pad=b[i+8:i+16]
    if pad!=b'\xaa'*8: print('pad break at',i,pad.hex()); break
    tot+=s;tags[t]=tags.get(t,0)+1;cnt+=1;i+=16
print('walked',cnt,'sum sizes',tot,'end',i,'file',len(b),'hdr+sizes',tot+8)
