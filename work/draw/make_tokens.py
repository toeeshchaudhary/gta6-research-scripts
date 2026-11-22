import re, itertools

def load(p):
    out = []
    for ln in open(p, encoding='utf-8', errors='replace'):
        for w in re.split(r'[^A-Za-z0-9_]+', ln.strip()):
            if 3 <= len(w) <= 28:
                out.append(w)
    return out

words = []
words += load(r'work/draw/tokens_veh.txt')
# names the archive itself declares (dense in plausible model names)
words += [ln.split('\t')[1] for ln in open(r'work/arch/dict/resnames_full.tsv', encoding='utf-8', errors='replace')
          if not ln.startswith('#') and len(ln.split('\t')) > 1]
words += load(r'work/arch/dict/tokens_words.txt')[:40000]

seen, keep = set(), []
for w in words:
    w = w.lower()
    if w in seen:
        continue
    seen.add(w)
    keep.append(w)
    if len(keep) >= 25000:
        break

with open(r'work/draw/tokens_mix.txt', 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(keep) + '\n')
print('tokens_mix', len(keep))
