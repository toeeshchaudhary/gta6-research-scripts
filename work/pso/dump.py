import sys, struct
p=sys.argv[1]; a=int(sys.argv[2],16); ln=int(sys.argv[3],16) if len(sys.argv)>3 else 4096
d=open(p,'rb').read()
end=min(len(d),a+ln)
for i in range(a,end,16):
    chunk=d[i:min(i+16,end)]
    hexs=' '.join(f'{b:02x}' for b in chunk)
    asc=''.join(chr(b) if 32<=b<127 else '.' for b in chunk)
    print(f"{i:06x}  {hexs:<47}  {asc}")
