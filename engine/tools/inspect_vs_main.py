import re, sys, struct

p = r'work\vs_main.spvasm'
L = open(p, encoding='utf-8').read().splitlines()
print('lines', len(L))
print([l.strip() for l in L if 'OpEntryPoint' in l or ('OpDecorate' in l and ('Location' in l or 'BuiltIn' in l or 'Binding' in l))])
c = {}
for l in L:
    m = re.match(r'\s*%(\d+) = OpConstant %\d+ (-?\d+)', l)
    if m:
        c['%' + m.group(1)] = int(m.group(2))
pc = [l.strip() for l in L if 'PushConstant' in l and 'OpVariable' in l]
print('push var:', pc)
# collect push-constant block indices used
pid = re.search(r'%(\d+) = OpVariable', pc[0]).group(1) if pc else None
used = set()
for l in L:
    m = re.search(r'OpAccessChain \S+ %' + pid + r' (.*)', l) if pid else None
    if m:
        for tok in m.group(1).split():
            used.add(c.get(tok, tok))
print('push indices used:', sorted(x for x in used if isinstance(x, int)))
# struct member offsets
print([l.strip() for l in L if 'OpMemberDecorate' in l][:8])
# what inputs are loaded (location vars)
for l in L:
    if 'OpLoad' in l and re.search(r'%[345]\b', l):
        pass
print('first 40 body lines:')
i = [k for k, l in enumerate(L) if 'OpFunction ' in l][0]
print('\n'.join(L[i:i + 40]))
