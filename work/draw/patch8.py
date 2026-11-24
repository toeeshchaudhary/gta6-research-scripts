p = 'work/draw/tool/ExtractModels/Program.cs'
s = open(p, encoding='utf-8').read()
s = s.replace('''            long approximateEnd = slice.Position;
            long searchStart = Math.Max(offset + 2, approximateEnd - 1_048_576);
            int tailLength = (int)(approximateEnd - searchStart);''',
'''            long approximateEnd = offset + slice.Position;   // slice.Position is relative to `offset`
            long searchStart = Math.Max(offset + 2, approximateEnd - 1_048_576);
            int tailLength = (int)(approximateEnd - searchStart);''')
open(p, 'w', encoding='utf-8').write(s)
print('patch8')
