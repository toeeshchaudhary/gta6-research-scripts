"""Task 1a: harvest every printable ASCII run from all readable plaintext corpora.

Saves:
  work/story/strings_all.txt   token<TAB>count<TAB>first_file:off
  work/story/s1_strings.out    summary + pattern hits
"""
import os, re, sys, json, collections

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
CORPORA = [
    ("groups_script", os.path.join(B, "work", "scripts", "out", "script_groups")),
    ("groups_story",  os.path.join(B, "work", "scripts", "out", "story_groups")),
    ("infl_script",   os.path.join(B, "work", "lineage", "bin", "Release", "net8.0", "out_script")),
    ("infl_common",   os.path.join(B, "work", "lineage", "bin", "Release", "net8.0", "out_common")),
    ("infl_story",    os.path.join(B, "work", "lineage", "bin", "Release", "net8.0", "out_story")),
    ("infl_data",     os.path.join(B, "work", "lineage", "bin", "Release", "net8.0", "out_data")),
    ("codec_exact",   os.path.join(B, "work", "codec", "full", "exact")),
    ("codec_zd",      os.path.join(B, "work", "codec", "full", "zeros_dict_unverified")),
    ("codec_dec",     os.path.join(B, "work", "codec", "dec")),
]
STR = re.compile(rb"[\x20-\x7e]{4,200}")

def main():
    counts = collections.Counter()
    first = {}
    per_corpus = {}
    for name, d in CORPORA:
        if not os.path.isdir(d):
            print("missing", d); continue
        nf = 0; nb = 0; ntok = 0
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if not os.path.isfile(p): continue
            data = open(p, "rb").read()
            nf += 1; nb += len(data)
            for m in STR.finditer(data):
                s = m.group(0).decode("latin-1").strip()
                if len(s) < 4: continue
                counts[s] += 1; ntok += 1
                if s not in first:
                    first[s] = f"{name}/{fn}:{m.start():x}"
        per_corpus[name] = (nf, nb, ntok, len(counts))
        print(f"{name}: files={nf} bytes={nb} tokens={ntok} distinct_total={len(counts)}", flush=True)
    with open(os.path.join(OUT, "strings_all.txt"), "w", encoding="utf-8") as f:
        for s, c in counts.most_common():
            f.write(f"{s}\t{c}\t{first[s]}\n")
    print(f"TOTAL distinct strings = {len(counts)}")

    pats = ["mission", "MI_", "_INT", "strand", "cutscene", "cs_", "cs%", "_cs",
            "script", "SCENARIO", "ambient", "WORLD", "STORY", "story",
            "michael", "franklin", "trevor", "lucia", "jason", "protagonist",
            "heist", "carsteal", "assassin", "traffic", "taxi", "vigilante",
            "psand", "ao_", "cut_", "intro", "finale", "credits"]
    print("\n== pattern hits ==")
    for p in pats:
        hits = [(s, c) for s, c in counts.items() if p.lower() in s.lower()]
        hits.sort(key=lambda x: -x[1])
        print(f"{p!r}: {len(hits)}")
        for s, c in hits[:12]:
            print(f"    {c:6d}  {s[:110]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
