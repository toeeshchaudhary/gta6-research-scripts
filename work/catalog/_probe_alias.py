import json, re, collections
M = json.load(open(r"work\catalog\out\_missions.json", encoding="utf-8"))
rows = []
for m in M:
    g = m["grid_texture"] or ""
    mm = re.match(r"^GRID_SML_L_(?:CH\d+_)?(.+)$", g)
    stem = mm.group(1) if mm else None
    d = m["description_key"] or ""
    dm = re.match(r"^PROG_(.+)_DESC_REPLAY$", d)
    dstem = dm.group(1) if dm else None
    rows.append((m["mission_id"], stem, dstem, m.get("chapter")))
diff = [r for r in rows if r[1] and r[1] != r[0]]
print("missions", len(rows), "grid stem differs from id:", len(diff))
for r in diff[:40]:
    print("  ", r)
same_desc = [r for r in rows if r[2] == r[1]]
print("desc stem == grid stem:", len(same_desc), "of", len(rows))
