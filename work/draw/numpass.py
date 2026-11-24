"""Enumerate <token>_<digits><letter> style model-name forms for the two big street hashes."""
import re, time

targets = {}
for ln in open(r'work/draw/targets2.txt', encoding='utf-8-sig'):
    p = ln.split()
    if p:
        targets[int(p[0], 16)] = p[1] if len(p) > 1 else '0'

toks = []
for ln in open(r'work/draw/tokens_veh.txt', encoding='utf-8'):
    s = ln.strip().lower()
    if 3 <= len(s) <= 24 and re.fullmatch(r'[a-z0-9_]+', s):
        toks.append(s)
pres = ['', 'veh_', 'v_', 'prop_', 'trailers_', 'trailer_', 'w_']
seps = ['', '_']
letters = 'abcdfgmnrstxyz'


def joaat(s):
    h = 0
    for c in s.encode():
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF


t0 = time.time()
tried, hits = 0, {}
# suffix forms: 01..999 plain and with a trailing letter, plus 2-digit+2 letters
forms = []
for n in range(1, 1000):
    forms.append(f'{n:02d}')
    for L in letters:
        forms.append(f'{n:02d}{L}')
    forms.append(f'{n:03d}')
for n in range(10, 100):
    for a in letters:
        for b in letters:
            forms.append(f'{n:02d}{a}{b}')

print('tokens', len(toks), 'forms', len(forms), 'pres', len(pres))
for p in pres:
    hp = 0
    for c in p.encode():
        hp = (hp + c) & 0xFFFFFFFF
        hp = (hp + (hp << 10)) & 0xFFFFFFFF
        hp ^= hp >> 6
    for t in toks:
        h1 = hp
        for c in t.encode():
            h1 = (h1 + c) & 0xFFFFFFFF
            h1 = (h1 + (h1 << 10)) & 0xFFFFFFFF
            h1 ^= h1 >> 6
        for sep in seps:
            base = p + t + sep
            h2 = h1
            if sep:
                h2 = (h2 + 0x5F) & 0xFFFFFFFF
                h2 = (h2 + (h2 << 10)) & 0xFFFFFFFF
                h2 ^= h2 >> 6
            for f in forms:
                h3 = h2
                for c in f.encode():
                    h3 = (h3 + c) & 0xFFFFFFFF
                    h3 = (h3 + (h3 << 10)) & 0xFFFFFFFF
                    h3 ^= h3 >> 6
                hv = (h3 + (h3 << 3)) & 0xFFFFFFFF
                hv ^= hv >> 11
                hv = (hv + (hv << 15)) & 0xFFFFFFFF
                tried += 1
                if hv in targets and hv not in hits:
                    hits[hv] = base + f
                    print('HIT', hex(hv), base + f, flush=True)
    print('  prefix', repr(p), tried, 'hits', len(hits), f'{time.time() - t0:.0f}s', flush=True)

with open(r'work/draw/hits_num.tsv', 'w', newline='\n') as fh:
    for hv, c in hits.items():
        fh.write(f'0x{hv:08X}\t{c}\n')
print('done', tried, 'candidates', len(hits), 'hits')
