import glob,os,struct,collections
files=sorted(glob.glob('work/codec/full/exact/*.bin'))+sorted(glob.glob('work/codec/full/zeros_dict_unverified/*.bin'))
print("plaintext blobs:",len(files),"bytes:",sum(os.path.getsize(f) for f in files))
tot=0
ptr=collections.Counter(); small=collections.Counter(); words=0
dwords=[]
for f in files:
    b=open(f,'rb').read(); tot+=len(b)
    n=len(b)//4
    words+=n
    for i in range(n):
        v=struct.unpack_from('<I',b,i*4)[0]
        dwords.append(v)
        if 0x50000000<=v<0x50100000: ptr[v]+=1
        if v<256: small[v]+=1
print("total dwords:",words)
print("0x50xxxxxx pointers:",sum(ptr.values()),"distinct:",len(ptr),"top:",ptr.most_common(6))
print("small ints <256:",sum(small.values()),"distinct:",len(small),"top:",small.most_common(10))
# high-byte distribution tells us if data looks like code or tables
hi=collections.Counter((v>>24)&0xff for v in dwords)
print("top high-bytes:",hi.most_common(8))
# 8-byte alignment: are pointers mostly at even dword indices?
idx=collections.Counter()
for f in files:
    b=open(f,'rb').read()
    for i in range(len(b)//4):
        v=struct.unpack_from('<I',b,i*4)[0]
        if 0x50000000<=v<0x50100000: idx[i%2]+=1
print("pointer parity (dword index mod 2):",dict(idx))
# repeated 16-byte record scan: find the most common stride where a field repeats
b=open(files[0],'rb').read()
print("\nfirst blob:",files[0],len(b),"bytes")
print("head:",b[:64].hex(' '))
