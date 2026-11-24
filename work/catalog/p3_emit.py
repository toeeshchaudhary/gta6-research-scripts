# p3_emit.py -- emit the per-mission catalogue, per-group files, unnamed-outline
# catalogues and the JSON master index.  Reads work/catalog/out/_*.json only.
import json, os, collections, textwrap

W = r"work"; OUT = os.path.join(W, "catalog", "out")
MD = os.path.join(OUT, "missions"); OD = os.path.join(OUT, "outlines")
os.makedirs(MD, exist_ok=True); os.makedirs(OD, exist_ok=True)

def jl(p): return json.load(open(p, encoding="utf-8"))
M = jl(os.path.join(OUT, "_missions.json"))
O = jl(os.path.join(OUT, "_outlines.json"))
S = jl(os.path.join(OUT, "_stats.json"))
COV = jl(os.path.join(OUT, "_coverage.json"))
CL = jl(os.path.join(OUT, "_clusters.json"))
PL = jl(os.path.join(OUT, "_placements.json"))
RANK = jl(os.path.join(W, "mission2", "out", "_ranking.json"))

def p(*a): print(*a, flush=True)

GROUP_NOTE = {
 "INT": "intro / interlude missions",
 "FT": "free-time or first-time beats",
 "COM": "common-world beats (shop, deal, drive prep)",
 "BIL": "Bilibili? no - BIL story branch beats (house, pick, wheel, finale)",
 "HO": "handover beats",
 "MTL": "motel strand",
 "CSC": "cutscene-driven strands (CSC_*)",
 "CLB": "club strand",
 "ROB": "robbery strand",
 "ANT": "Antonia / ANT strand",
 "AO": "AO deal strand",
 "BAN": "banco (bank) strand",
 "SFH": "safehouse strand",
 "MNY": "money strand",
 "AIR": "air strand",
 "COA": "coa strand",
 "CTI": "cut-in / trigger beats",
 "UP": "upgrade/prep beats",
 "FIN": "finale",
 "misc": "no underscore-separated prefix (legacy ids)",
}
GROUP_NOTE["BIL"] = "BIL strand (house, pick, wheel, finale, boss)"
GROUP_NOTE["ANT"] = "ANT strand (intro, chase, recovery)"

# ---------------------------------------------------------------- helpers
def phase_tags(o):
    seen = [x for x in o["phases"] if x]
    order = ["setup", "cutscene", "action", "law", "aftermath", "exit"]
    s = sorted(set(seen), key=lambda x: order.index(x) if x in order else 99)
    return ",".join(s) if s else "-"

def flow_md(txt, width=160):
    if len(txt) <= width: return "`%s`" % txt
    return "`%s`" % txt

POS = jl(os.path.join(OUT, "_posread.json"))
POSNOTE = POS["posnote"]

def outline_notes(o):
    """Provenance footnotes for one outline: expanded-vocabulary names and position-only reads."""
    out = []
    newn = sorted({(st["name"], st["name_src"]) for st in o["states"]
                   if st.get("name_src", "").startswith(("C:", "A:"))})
    if newn:
        out.append("names from the expanded vocabulary (§V): " +
                   ", ".join("`%s` (%s)" % (nm, src) for nm, src in newn))
    poss = [st for st in o["states"] if st.get("pos")]
    if poss:
        out.append("position-only reads (no name exists): " +
                   "; ".join("`%s` %s — %s" % (st["hash"], st["pos"], POSNOTE.get(st["hash"], ""))
                             for st in poss))
    return out

def legibility(o):
    if o["structural_only"]: return "C"
    if o["named_real_states"] == o["real_states"]: return "A"
    if o["named_states"] > 0: return "B"
    return "C"

# ---------------------------------------------------------------- per-group mission md
groups = collections.defaultdict(list)
for m in M: groups[m["group"]].append(m)

def mission_block(m):
    L = []
    L.append("### `%s`" % m["mission_id"])
    kinds = ", ".join("%s x%d" % (k, v) for k, v in sorted(m["doc_kinds"].items()))
    L.append("")
    L.append("| field | value | provenance |")
    L.append("|---|---|---|")
    L.append("| mission id | `%s` | **proven** — literal in `missions_common_rpf.txt` / `CMissions` |" % m["mission_id"])
    if m["description_key"]:
        L.append("| description key | `%s` | **proven** — the `PROG_*_DESC_REPLAY` string in the CMissions document |" % m["description_key"])
    if m["grid_texture"]:
        L.append("| grid texture | `%s` | **proven** — the `GRID_SML_L_*` string in the CMissions document |" % m["grid_texture"])
    if m.get("chapter"):
        L.append("| chapter | CH%d | **proven** as a string: `CH%d` is literal in the grid-texture name; the reading \"chapter %d\" is **inferred** |"
                 % (m["chapter"], m["chapter"], m["chapter"]))
    else:
        L.append("| chapter | — | no `CH<n>` token in the grid-texture name |")
    if m.get("asset_stem") and m["asset_stem"] != m["mission_id"]:
        L.append("| asset stem | `%s` | **proven** string: this mission's grid texture and description key use `%s`, not its own id — its assets are shared with another id |"
                 % (m["asset_stem"], m["asset_stem"]))
    L.append("| content docs | %d (%s) | **proven** — mission id literal in the doc's mission table |" % (len(m["docs"]), kinds or "-"))
    if m["weapon_loadouts"]:
        def wname(x):
            return x.get("preset") or x.get("name") or json.dumps(x, sort_keys=True)
        ws = "; ".join("%s → %s" % (w["name"], ", ".join(wname(x) for x in w["weapons"]) or "no preset")
                       for w in m["weapon_loadouts"])
        L.append("| weapon kit | %s | **proven** — literal `LO_<ID>_` in `CPedInventoryLoadOutManager` |" % ws.replace("|", "/"))
    else:
        L.append("| weapon kit | — | absent from the 28-mission loadout table |")
    if m["vehicle_tint_presets"]:
        L.append("| vehicle tint | %s | **proven** — literal `_<ID>_` in `CPaletteIndexedRecipeTintsArray` |"
                 % ", ".join("`%s`" % x if isinstance(x, str) else "`%s`" % json.dumps(x) for x in m["vehicle_tint_presets"]))
    else:
        L.append("| vehicle tint | — | no preset in the 7-mission tint table |")
    if m["lighting_modifiers"]:
        L.append("| lighting preset | %s | **proven** — literal `_<ID>_` in `timecycle_modifier_data` |"
                 % ", ".join("`%s`" % x if isinstance(x, str) else "`%s`" % json.dumps(x) for x in m["lighting_modifiers"]))
    else:
        L.append("| lighting preset | — | no modifier in the 5-mission lighting table |")
    if m["manifest_content_files"] or m["manifest_content_sets"]:
        L.append("| content sets/files | %s / %s | **provisional** — id inside content-set id or path |"
                 % (", ".join(map(str, m["manifest_content_sets"])) or "—",
                    ", ".join(map(str, m["manifest_content_files"]))[:200] or "—"))
    banks = m["bundled_cutscene_banks"] or m["banks_exact_prefix"]
    if banks:
        L.append("| cutscene audio banks | %d bank(s): %s | **provisional** — `<ID>AU_` bank-name prefix in the game's own string table |"
                 % (len(banks), ", ".join("`%s`" % b for b in banks[:6]) + (" …" if len(banks) > 6 else "")))
    else:
        L.append("| cutscene audio banks | — | no bank name starts with `<ID>AU_` |")
    if m["outline_id"]:
        o = O[m["outline_id"]]
        L.append("| state outline | `%s` (%d records, %d states, %d named) | **proven** — joaat(id) is a record key in this file only |"
                 % (m["outline_id"], o["records"], o["state_count"], o["named_states"]))
    else:
        L.append("| state outline | — | **unresolved** — no mission→file binding exists (only `robbergetawaydriverprep`→`g1730`) |")
    L.append("")
    if m["outline_id"]:
        o = O[m["outline_id"]]
        L.append("**State flow** (`→` is stored file order, *not* play order; `~` = structural key, not a state name):")
        L.append("")
        L.append("```")
        for line in textwrap.wrap(o["txt"], 150, subsequent_indent="  "):
            L.append(line)
        L.append("```")
        L.append("")
        L.append("Phases present: %s · legibility %s · entity elements %d" %
                 (phase_tags(o) or "none", legibility(o), o["entities"]))
        L.append("")
        for note in outline_notes(o):
            L.append("*%s*" % note)
            L.append("")
    return L

for g, ms in sorted(groups.items()):
    ms.sort(key=lambda x: x["mission_id"])
    md = ["# Mission group `%s` — %s" % (g, GROUP_NOTE.get(g, "")), "",
          "%d mission id(s). Grouping is by the mission-id prefix (a naming convention in `CMissions`), "
          "**not** a proven chapter grouping." % len(ms), ""]
    for m in ms:
        md += mission_block(m)
    open(os.path.join(MD, g + ".md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(ms, open(os.path.join(MD, g + ".json"), "w", encoding="utf-8"), indent=1)
p("wrote per-group files:", len(groups))

# ---------------------------------------------------------------- unnamed outline catalogue
un = [o for o in O.values() if not any(m["outline_id"] == o["id"] for m in M)]
un.sort(key=lambda o: o["id"])
p("unnamed outlines:", len(un))

by_leg = collections.defaultdict(list)
for o in un: by_leg[legibility(o)].append(o)

idx_rows = []
CH = 250
for k in range(0, len(un), CH):
    chunk = un[k:k + CH]
    md = ["# Unnamed mission outlines — part %d (%d of %d)" % (k // CH + 1, len(chunk), len(un)), "",
          "These 2,035 outline files have **no provable mission id**. `→` is stored file order, not play order.",
          "`~` marks a structural key (a packed value that landed in the key column, not a state name).", "",
          "| id | rec | states | named/real | phases | entities | legibility |",
          "|---|---|---|---|---|---|---|"]
    for o in chunk:
        md.append("| `%s` | %d | %d | %d/%d | %s | %d | %s |" %
                  (o["id"], o["records"], o["state_count"], o["named_states"], o["real_states"],
                   phase_tags(o), o["entities"], legibility(o)))
    md.append("")
    md.append("## State flows")
    md.append("")
    for o in chunk:
        md.append("**`%s`** — %d records, %d states, %d named, %d entity elements, phases: %s" %
                  (o["id"], o["records"], o["state_count"], o["named_states"], o["entities"], phase_tags(o)))
        md.append("")
        md.append("```")
        for line in textwrap.wrap(o["txt"], 150, subsequent_indent="  "):
            md.append(line)
        md.append("```")
        for note in outline_notes(o):
            md.append("")
            md.append("*%s*" % note)
        md.append("")
    open(os.path.join(OD, "UNNAMED_%02d.md" % (k // CH + 1)), "w", encoding="utf-8").write("\n".join(md) + "\n")

json.dump([{"id": o["id"], "records": o["records"], "state_count": o["state_count"],
            "named_states": o["named_states"], "real_states": o["real_states"],
            "entities": o["entities"], "structural_only": o["structural_only"],
            "phases": [x for x in o["phases"] if x], "legibility": legibility(o),
            "new_names": sorted({st["name"] for st in o["states"]
                                 if st.get("name_src", "").startswith(("C:", "A:"))}),
            "positional": sorted({st["hash"] for st in o["states"] if st.get("pos")}),
            "flow": o["txt"]} for o in un],
          open(os.path.join(OD, "unnamed_outlines.json"), "w", encoding="utf-8"), indent=1)
p("wrote unnamed parts:", (len(un) + CH - 1) // CH)

# ---------------------------------------------------------------- master JSON index
master = {
  "generated_by": "work/catalog/p1_index.py,p2_stats.py,p3_emit.py",
  "trust_legend": {
    "proven": "literal string/hash match in a named document, or a count/byte fact",
    "measured": "statistic with its denominator stated",
    "provisional": "name from the brute-force vocabulary (joaat preimage, register plausible) or a prefix rule",
    "unresolved": "8-hex hash, no name"},
  "counts": COV,
  "missions": M,
  "outline_index": [{"id": o["id"], "records": o["records"], "state_count": o["state_count"],
                     "named_states": o["named_states"], "real_states": o["real_states"],
                     "named_real_states": o["named_real_states"], "entities": o["entities"],
                     "phases": [x for x in o["phases"] if x], "legibility": legibility(o),
                     "structural_only": o["structural_only"], "flow": o["txt"]}
                    for o in sorted(O.values(), key=lambda x: x["id"])],
  "clusters": CL, "placements": PL,
  "binding": {"mission_id": "robbergetawaydriverprep", "outline_id": "g1730_045AE000",
              "provenance": "proven", "records": O["g1730_045AE000"]["records"]},
}
json.dump(master, open(os.path.join(OUT, "catalog_index.json"), "w", encoding="utf-8"), indent=1)
p("wrote catalog_index.json", os.path.getsize(os.path.join(OUT, "catalog_index.json")))
