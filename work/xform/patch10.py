p=r"work\xform\xtool\Program.cs"
s=open(p,encoding="utf-8").read()
s=s.replace('if (!(e10 == 1 || e10 == 2 || e10 == 4)) return false;','if (e10 > 8) return false;')
open(p,"w",encoding="utf-8").write(s)
