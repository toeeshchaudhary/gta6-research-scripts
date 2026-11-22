p=r"work\xform\xtool\Program.cs"
s=open(p,encoding="utf-8").read()
s=s.replace("        static List<byte[]> InflateBlocks(FileStream fs, long offset, out List<long> packed)\n        {\n            var blocks = new List<byte[]>();",
 "        static bool FastMode = false;\n\n        static List<byte[]> InflateBlocks(FileStream fs, long offset, out List<long> packed)\n        {\n            var blocks = new List<byte[]>();\n            if (FastMode)\n            {\n                packed = new List<long>();\n                long c;\n                byte[] d0 = InflateSlice(fs, offset, fs.Length - offset, out c);\n                if (d0 != null) { blocks.Add(d0); packed.Add(c); }\n                return blocks;\n            }",1)
s=s.replace('            int threads = a.Length > 4 ? int.Parse(a[4]) : 6;\n            long[] offs = LoadOffsets(candFile);\n            int total = offs.Length;\n            if (a.Length > 5) total = Math.Min(total, int.Parse(a[5]));\n            string donePath = outPrefix + "_done.txt";',
 '            int threads = a.Length > 4 ? int.Parse(a[4]) : 6;\n            FastMode = a.Length > 6 && a[6] == "fast";\n            long[] offs = LoadOffsets(candFile);\n            int total = offs.Length;\n            if (a.Length > 5) total = Math.Min(total, int.Parse(a[5]));\n            string donePath = outPrefix + "_done.txt";',1)
s=s.replace('Console.WriteLine($"candidates={total:N0} already={done.Count:N0} threads={threads}");',
 'Console.WriteLine($"candidates={total:N0} already={done.Count:N0} threads={threads} fast={FastMode}");',1)
open(p,"w",encoding="utf-8").write(s)
print("ok")
