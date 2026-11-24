# p2_stats.py -- coverage numbers + phase roll-ups for the catalogue
import json, os, collections
W = r"work"; OUT = os.path.join(W, "catalog", "out")
M = json.load(open(os.path.join(OUT, "_missions.json"), encoding="utf-8"))
O = json.load(open(os.path.join(OUT, "_outlines.json"), encoding="utf-8"))
S = json.load(open(os.path.join(OUT, "_stats.json"), encoding="utf-8"))
CL = json.load(open(os.path.join(OUT, "_clusters.json"), encoding="utf-8"))
P = json.load(open(os.path.join(OUT, "_placements.json"), encoding="utf-8"))

def p(*a): print(*a, flush=True)

p("missions", len(M))
c = collections.Counter()
for m in M:
    c["any_asset"] += 1 if (m["weapon_loadouts"] or m["vehicle_tint_presets"] or m["lighting_modifiers"]
                            or m["manifest_content_files"] or m["bundled_cutscene_banks"] or m["banks_exact_prefix"]) else 0
    c["weapon"] += 1 if m["weapon_loadouts"] else 0
    c["tint"] += 1 if m["vehicle_tint_presets"] else 0
    c["light"] += 1 if m["lighting_modifiers"] else 0
    c["content"] += 1 if (m["manifest_content_files"] or m["manifest_content_sets"]) else 0
    c["bundled_banks"] += 1 if m["bundled_cutscene_banks"] else 0
    c["banks_exact"] += 1 if m["banks_exact_prefix"] else 0
    c["banks_loose]"] = 0
    c["banks_loose"] += 1 if m["banks_loose_prefix"] else 0
    c["docs"] += 1 if m["docs"] else 0
    c["outline"] += 1 if m["outline_id"] else 0
    c["desc_key"] += 1 if m["description_key"] else 0
    c["grid_tex"] += 1 if m["grid_texture"] else 0
p(dict(c))
p("groups", collections.Counter(m["group"] for m in M).most_common())

# outline-side
tot = len(O)
structural_only = sum(1 for o in O.values() if o["structural_only"])
named_any = sum(1 for o in O.values() if o["named_states"] > 0)
full_named = sum(1 for o in O.values() if o["real_states"] > 0 and o["named_real_states"] == o["real_states"])
ent = sum(1 for o in O.values() if o["entities"] > 0)
recs = sum(o["records"] for o in O.values())
p("outlines", tot, "structural_only", structural_only, "named_any", named_any,
  "fully_named_real", full_named, "with_entities", ent, "records", recs)
p("states total", sum(o["state_count"] for o in O.values()),
  "real states", sum(o["real_states"] for o in O.values()),
  "named real", sum(o["named_real_states"] for o in O.values()))
p("entities total", sum(o["entities"] for o in O.values()))
sz = collections.Counter()
for o in O.values():
    r = o["records"]
    sz["0" if r == 0 else "1-9" if r < 10 else "10-49" if r < 50 else "50-199" if r < 200 else "200+"] += 1
p("size classes", dict(sz))

# phase presence per file
PH = ["setup", "cutscene", "action", "law", "aftermath", "exit"]
fp = collections.Counter()
fpb = collections.Counter()
for o in O.values():
    s = set(x for x in o["phases"] if x)
    b = set(x for x in o.get("phases_before", []) if x)
    for k in s: fp[k] += 1
    for k in b: fpb[k] += 1
    fp["_files_with_any_phase"] += 1 if s else 0
    fpb["_files_with_any_phase"] += 1 if b else 0
p("files with each phase (after overlay)", dict(fp))
p("files with each phase (before overlay)", dict(fpb))

prim_a = collections.Counter(x for o in O.values() for x in o["phases"] if x)
prim_b = collections.Counter(x for o in O.values() for x in o.get("phases_before", []) if x)
p("primary states before", dict(prim_b), sum(prim_b.values()))
p("primary states after ", dict(prim_a), sum(prim_a.values()))


# keyword predicates for structural completeness
def has(o, *subs):
    names = [st["name"].lower() for st in o["states"] if st["name"]]
    return any(any(s in n for s in subs) for n in names)

pred = collections.Counter()
for o in O.values():
    i = has(o, "intro"); x = has(o, "outro", "exit", "leave")
    a = "action" in o["phases"]; lw = "law" in o["phases"]; af = "aftermath" in o["phases"]
    pred["has_intro"] += i; pred["has_outro"] += x
    pred["intro+outro"] += (i and x)
    pred["intro+outro+action"] += (i and x and a)
    pred["law"] += lw; pred["aftermath"] += af
    sv = has(o, "steal"); dv = has(o, "deliver", "dropoff")
    pred["steal"] += sv; pred["deliver"] += dv
    pred["steal+deliver"] += (sv and dv)
    pred["sealed_triad"] += (i and x and (a or af))
p("predicates", dict(pred))

p("clusters>1", len(CL), "files", sum(x["n"] for x in CL))
p("top clusters", [(x["n"], x["files"][0]) for x in CL[:12]])
json.dump({"mission_coverage": dict(c), "outline_shape": {
    "outlines": tot, "structural_only": structural_only, "named_any": named_any,
    "fully_named_real": full_named, "with_entities": ent, "records": recs,
    "states_total": sum(o["state_count"] for o in O.values()),
    "real_states": sum(o["real_states"] for o in O.values()),
    "named_real_states": sum(o["named_real_states"] for o in O.values()),
    "entities_total": sum(o["entities"] for o in O.values()),
    "size_classes": dict(sz)},
    "file_phases": dict(fp), "file_phases_before": dict(fpb), "predicates": dict(pred),
    "primary_states_before": dict(prim_b), "primary_states_after": dict(prim_a),
    "vocab": S.get("vocab", {}),
    "placements": {k: {"entities": v["entities"], "archetypes": v["archetypes"],
                       "records": v["records"], "states": v["states"]} for k, v in P.items()}},
    open(os.path.join(OUT, "_coverage.json"), "w", encoding="utf-8"), indent=1)
