import sys, struct, os, collections
p = sys.argv[1]
d = open(p,'rb').read()
print("len", len(d))
tags = [b'PSIN',b'LSCH',b'LENM',b'LSNS',b'LGID',b'LRSC',b'CHKS']
# walk chunks
off = 0
while off + 8 <= len(d):
    t = d[off:off+4]
    ln = struct.unpack('>I', d[off+4:off+8])[0]
    print(f"chunk {t!r} at 0x{off:x} len {ln} (ends 0x{off+ln:x})")
    off += ln
if off != len(d): print("TILING MISMATCH: end", off, "len", len(d))
