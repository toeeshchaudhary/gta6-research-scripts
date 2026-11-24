import struct
def load(p):
    b=open(p,"rb").read()
    assert struct.unpack("<I",b[:4])[0]==0x314D5246, "magic"
    nb=struct.unpack("<i",b[4:8])[0]
    o=8; meta=[]
    for i in range(nb):
        pl=struct.unpack("<q",b[o:o+8])[0]; il=struct.unpack("<i",b[o+8:o+12])[0]; meta.append((pl,il)); o+=12
    blocks=[]; p=o
    for pl,il in meta:
        blocks.append(b[p:p+il]); p+=il
    return meta,blocks
meta,blocks=load(r"work\xform\out\fe970B010.bin")
print("meta",meta, [len(x) for x in blocks])
b0=blocks[0]
print("len",len(b0))
for i in range(0,0x120,8):
    v=struct.unpack("<Q",b0[i:i+8])[0]
    tag=""
    if 0x50000000<=v<0x51000000:
        loc=v-0x50000000; tag="SYS ptr -> 0x%X"%loc
        if loc < len(b0):
            s=b0[loc:loc+80].split(b"\x00")[0]
            try:
                t=s.decode()
                if t: tag+="  '%s'"%t
            except: pass
    elif 0x60000000<=v<0x70000000: tag="GFX ptr -> 0x%X"%(v-0x60000000)
    print("%04X %016X %s"%(i,v,tag))
