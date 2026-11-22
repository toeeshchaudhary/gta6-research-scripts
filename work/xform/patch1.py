import re
p=r"work\xform\xtool\Program.cs"
s=open(p,encoding="utf-8").read()
s=s.replace('int idx0 = BinaryPrimitives.ReadUInt16LittleEndian(b.AsSpan(o + 0x1A, 2));','int idx0 = b[o + 0x1B];')
s=s.replace('int idx = BinaryPrimitives.ReadUInt16LittleEndian(b.AsSpan(o + 0x1A, 2));','int idx = b[o + 0x1B];')
s=s.replace('if (wantIdx < 0) { if (idx > 64) return false; }','if (wantIdx < 0) { }')
open(p,"w",encoding="utf-8").write(s)
print("patched")
