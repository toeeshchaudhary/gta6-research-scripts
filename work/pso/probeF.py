import struct,glob,os,collections
files=[]
for pat in ('script_pages','story_groups'):
    files += glob.glob(os.path.join(r'work\scripts\out',pat,'*.bin'))
lane_inrange=collections.Counter(); lane_small=collections.Counter(); lane_hash=collections.Counter()
tot=0
for f in files[:600]:
    d=open(f,'rb').read()
    i=d.find(b'LSCH')
    if i<0: continue
    ln=struct.unpack('>I',d[i+4:i+8])[0]; body=d[i+8:i+ln]
    n=body[9] if len(body)>15 else 0
    if not (0<n<=40): continue
    o=16; recs=[]; ok=True
    for k in range(n):
        if o+32>len(body) or body[o:o+8]!=b'\xaa'*8: ok=False;break
        recs.append((body[o+8],struct.unpack('<H',body[o+14:o+16])[0],struct.unpack('<I',body[o+16:o+20])[0])); o+=32
    if not ok: continue
    for (sl,cnt,nm) in recs:
        for e in range(cnt):
            p=o; 
            if p+16>len(body): break
            lanes=struct.unpack('<IIII',body[p:p+16]); o+=16; tot+=1
            for L,v in enumerate(lanes):
                if v<sl: lane_inrange[L]+=1
                if v<=0x21: lane_small[L]+=1
                if v>0x10000: lane_hash[L]+=1
print("entries",tot)
print("lane < structLen:",lane_inrange.most_common(4))
print("lane <=0x21    :",lane_small.most_common(4))
print("lane >0x10000  :",lane_hash.most_common(4))
