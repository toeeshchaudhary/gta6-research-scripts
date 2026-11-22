p = 'work/draw/tool/ExtractModels/Program.cs'
s = open(p, encoding='utf-8').read()
s = s.replace('''            if (offset < 16 || offset > file.Length - 6) return false;''',
              '''            if (offset < 16 || offset > file.Length - 6) { why = "offset out of range"; return false; }''')
s = s.replace('''            if (tailLength <= 0) return false;''',
              '''            if (tailLength <= 0) { why = $"tail {tailLength} at {approximateEnd}"; return false; }''')
s = s.replace('''            if (file.Read(tail, 0, tailLength) != tailLength) return false;''',
              '''            if (file.Read(tail, 0, tailLength) != tailLength) { why = "short tail read"; return false; }''')
open(p, 'w', encoding='utf-8').write(s)
print('patch7')
