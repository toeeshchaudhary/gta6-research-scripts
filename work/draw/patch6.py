p = 'work/draw/tool/ExtractModels/Program.cs'
s = open(p, encoding='utf-8').read()

s = s.replace(
    'private bool Inflate(FileStream file, long offset, int maximum, out Block block)',
    'private bool Inflate(FileStream file, long offset, int maximum, out Block block, ref string why)')
s = s.replace(
    '''            file.Position = offset;
            Span<byte> header = stackalloc byte[2];
            if (file.Read(header) != 2) return false;''',
    '''            file.Position = offset;
            Span<byte> header = stackalloc byte[2];
            if (file.Read(header) != 2) { why = "short read"; return false; }''')
s = s.replace(
    '''                (header[1] & 32) != 0) return false;''',
    '''                (header[1] & 32) != 0) { why = "bad zlib header"; return false; }''')
s = s.replace('if (output.Length + n > maximum) return false;',
              'if (output.Length + n > maximum) { why = "over max"; return false; }')
s = s.replace('if (output.Length < 8) return false;',
              'if (output.Length < 8) { why = "short output"; return false; }')
s = s.replace('''            if (packed < 0) return false;''',
              '''            if (packed < 0) { why = "adler not found"; return false; }''')
s = s.replace('''            return false;
        }
    }

    private sealed class SliceStream''',
              '''            why = "adler mismatch";
            return false;
        }
    }

    private sealed class SliceStream''')

s = s.replace('if (!Inflate(file, next, RageModelDecoder.MaxSystemBytes, out Block first))',
              'string why0 = "";\n            if (!Inflate(file, next, RageModelDecoder.MaxSystemBytes, out Block first, ref why0))')
s = s.replace('return Row(offset, name, hash, "fail", 0, 0, "-", "system block did not inflate");',
              'return Row(offset, name, hash, "fail", 0, 0, "-", "system block did not inflate: " + why0);')
s = s.replace('out Block more)) break;', 'out Block more, ref why0)) break;')
s = s.replace('out Block extra)) break;', 'out Block extra, ref why0)) break;')

open(p, 'w', encoding='utf-8').write(s)
print('patch6 applied')
