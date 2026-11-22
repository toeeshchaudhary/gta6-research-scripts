import collections, json, re
rows = []
for ln in open(r"work\brute\hits_family.txt", encoding="utf-8", errors="replace"):
    p = ln.rstrip("\n").split("\t")
    if len(p) < 3: continue
    rows.append((p[0].strip().lower(), int(p[1]), p[2]))
by = collections.defaultdict(list)
for h, o, n in rows: by[h].append((o, n))
canon = {h: sorted({n for _, n in v}, key=lambda s: (len(s), s))[0] for h, v in by.items()}
occ = {h: max(o for o, _ in v) for h, v in by.items()}

O = json.load(open(r"work\catalog\out\_outlines.json", encoding="utf-8"))
struct_hits = collections.Counter()
real_hits = collections.Counter()
for o in O.values():
    for st in o["states"]:
        if st["hash"] in canon:
            (struct_hits if st["structural"] else real_hits)[st["hash"]] += 1
print("overlay hashes as non-structural states:", len(real_hits))
print("overlay hashes as structural states:", len(struct_hits), list(struct_hits.items())[:10])
print("both:", len(set(struct_hits) & set(real_hits)))
# names appearing as structural
for h in list(struct_hits)[:12]:
    print("  ", h, canon[h], occ[h], "struct", struct_hits[h], "real", real_hits.get(h, 0))
# vocabB check for c7530b3c
vb = {}
for ln in open(r"work\mission2\vocabB.tsv", encoding="utf-8", errors="replace"):
    p = ln.rstrip("\n").split("\t")
    if len(p) >= 2 and re.match(r"^[0-9a-f]{8}$", p[0]): vb[p[0].lower()] = p[1]
print("c7530b3c in vocabB?", vb.get("c7530b3c"))
print("n vocabB", len(vb))
