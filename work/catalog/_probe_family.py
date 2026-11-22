import collections, re, json
p = r"work\brute\hits_family.txt"
rows = []
for ln in open(p, encoding="utf-8", errors="replace"):
    parts = ln.rstrip("\n").split("\t")
    if len(parts) < 3: continue
    h, occ, name = parts[0].strip().lower(), parts[1], parts[2]
    rows.append((h, name, parts[3] if len(parts) > 3 else ""))
by = collections.defaultdict(list)
for h, name, src in rows: by[h].append(name)
print("lines", len(rows), "distinct hashes", len(by))
print("case variants per hash:", collections.Counter(len(v) for v in by.values()))
# canonical = shortest then alphabetically first
canon = {h: sorted(set(v), key=lambda x: (len(x), x))[0] for h, v in by.items()}
print("sample:")
for h in list(by)[:6]: print(" ", h, sorted(set(by[h])))
# compare against mission2 vocabB (tier B) and outlines
vb = {}
for ln in open(r"work\mission2\vocabB.tsv", encoding="utf-8", errors="replace"):
    parts = ln.rstrip("\n").split("\t")
    if len(parts) >= 2 and re.match(r"^[0-9a-f]{8}$", parts[0]):
        vb[parts[0].lower()] = parts[1]
va = {}
for ln in open(r"work\mission2\vocabA.tsv", encoding="utf-8", errors="replace"):
    parts = ln.rstrip("\n").split("\t")
    if len(parts) >= 2 and re.match(r"^[0-9a-f]{8}$", parts[0]):
        va[parts[0].lower()] = parts[1]
print("tierA", len(va), "tierB", len(vb))
new = [h for h in by if h not in vb and h not in va]
print("family hits not already in A/B:", len(new))
print("family hits already in B:", sum(1 for h in by if h in vb))
O = json.load(open(r"work\catalog\out\_outlines.json", encoding="utf-8"))
seen = collections.Counter()
for o in O.values():
    for st in o["states"]:
        if not st["structural"]:
            seen[st["hash"]] += 1
inn = [h for h in by if h in seen]
print("family hashes that actually occur as non-structural outline states:", len(inn))
print("of those, new (not in A/B):", sum(1 for h in inn if h not in vb and h not in va))
json.dump({"canon": canon, "distinct": len(by), "in_outlines": len(inn)}, open(r"work\catalog\out\_family_raw.json", "w"), indent=1)
