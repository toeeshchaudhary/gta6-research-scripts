p=r"work\xform\xtool\Program.cs"
s=open(p,encoding="utf-8").read()
s=s.replace('''            uint tr = BinaryPrimitives.ReadUInt32LittleEndian(b.AsSpan(o + 0x30, 4));
            if (!(tr == 0 || tr == 0x02080000 || tr == 0x00004000 || tr == 0x00020000)) return false;''','')
open(p,"w",encoding="utf-8").write(s)
