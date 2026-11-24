import struct
b=open(r'.\work\scripts\out\story_groups\g1730_045AE000.bin','rb').read()
for off,size in ((11248,448),(38032,224)):
    print('== chunk',off)
    i=off+16
    while i<off+size-15:
        d=struct.unpack_from('<8I',b,i)
        ok = d[1]==0 and d[5]==0 and d[7]==0 and d[0]!=0
        print(i, 'OK' if ok else 'BAD', [hex(x) for x in d])
        i+=32
