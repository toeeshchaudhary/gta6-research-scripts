import collections, re, json
rows = []
for ln in open(r"work\brute\hits_family.txt", encoding="utf-8", errors="replace"):
    parts = ln.rstrip("\n").split("\t")
    if len(parts) < 3: continue
    rows.append((parts[0].strip().lower(), int(parts[1]), parts[2]))
by = collections.defaultdict(list)
for h, occ, name in rows: by[h].append((occ, name))
canon = {}
occ_of = {}
for h, v in by.items():
    occ = max(x[0] for x in v)
    names = sorted({x[1] for x in v}, key=lambda s: (len(s), s))
    canon[h] = names[0]
    occ_of[h] = occ
print("distinct", len(canon))
for want in ["disrupt", "onfootcomplete", "dropoff", "saveped", "shootout", "lawaftermath", "windowfight", "boatchase", "ambientvehicle", "robberycombat"]:
    hits = [h for h, n in canon.items() if n.lower() == want]
    print(want, "->", hits, [occ_of[h] for h in hits])
print("top by occ:", sorted(((occ_of[h], h, canon[h]) for h in canon), reverse=True)[:12])
print("c7530b3c in family?", "c7530b3c" in canon)
print("84ba0a3a (HOPOUT)?", canon.get("84ba0a3a"))
