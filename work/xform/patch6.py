p=r"work\xform\xtool\Program.cs"
s=open(p,encoding="utf-8").read()
s=s.replace('''        static int CmdTabs1(string[] a)
        {
            long off = ParseHex(a[2]);''','''        static int CmdTabs1(string[] a)
        {
            if (a.Length > 3 && a[3] == "fast") FastMode = true;
            long off = ParseHex(a[2]);''')
open(p,"w",encoding="utf-8").write(s)
