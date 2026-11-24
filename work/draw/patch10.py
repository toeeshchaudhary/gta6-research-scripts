p = 'work/draw/tool/Core/RageModelDecoder.cs'
s = open(p, encoding='utf-8').read()
s = s.replace('using System.Buffers.Binary;',
              'using System.Buffers.Binary;\nusing System.Runtime.CompilerServices;')
s = s.replace('private static void Check(bool condition) { if (!condition) throw new InvalidDataException("Unsupported model ownership layout."); }',
              'private static void Check(bool condition, [CallerArgumentExpression(nameof(condition))] string? e = null) '
              '{ if (!condition) throw new InvalidDataException("own: " + e); }')
s = s.replace('private static void Require(bool condition) { if (!condition) throw new InvalidDataException("Unsupported or inconsistent drawable layout."); }',
              'private static void Require(bool condition, [CallerArgumentExpression(nameof(condition))] string? e = null) '
              '{ if (!condition) throw new InvalidDataException("req: " + e); }')
open(p, 'w', encoding='utf-8').write(s)
print('patched requires')
