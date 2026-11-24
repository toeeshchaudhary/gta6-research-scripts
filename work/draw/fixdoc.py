p = 'DRAW.md'
s = open(p, encoding='utf-8').read()
s = s.replace('* Failures are real: 99 resources do not decode',
              '* Failures are real: 98 resources still do not decode (99 in the batch, one fixed and re-run)')
s = s.replace('**0 hits on `0x2F7E64D1` and `0xD3E22D9A` over all 529 M candidates**, which is far below the ~1.1\nexpected collisions, so the null result is real: those names are not',
              '**0 hits on `0x2F7E64D1` and `0xD3E22D9A` over all 529 M candidates** (0.25 expected accidental\ncollisions for these two targets, 0 observed), so the null result stands: those names are not')
s = s.replace('including the four decoder bugs', 'including the five decoder bugs')
open(p, 'w', encoding='utf-8').write(s)
print('fixed')
