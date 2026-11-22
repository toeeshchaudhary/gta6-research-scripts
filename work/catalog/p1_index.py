# p1_index.py -- join layer for the per-mission catalogue.
# Reads only existing artefacts; writes work/catalog/out/_*.json
import json, os, glob, collections, statistics

W = r"work"
OUT = os.path.join(W, "catalog", "out")
os.makedirs(OUT, exist_ok=True)

def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def log(*a):
    print(*a, flush=True)

# ---------------------------------------------------------------- sources
missions = [l.strip() for l in open(os.path.join(W, "story", "missions_common_rpf.txt"),
                                   encoding="utf-8", errors="replace") if l.strip()]
log("mission ids:", len(missions))

mmap = jload(os.path.join(W, "meta", "run", "mission_map.json"))
bundles = {(b["mission_id"]): b for b in jload(os.path.join(W, "manifest", "out", "mission_bundles.json"))["bundles"]}
log("mission_map:", len(mmap), "bundles:", len(bundles))
log("ids in list not in bundles:", [m for m in missions if m not in bundles][:5])

bankmap = jload(os.path.join(W, "bind", "out", "cutscene_bank_map.json"))
banks = bankmap["banks"]          # bank -> {cutscenes, count, namespace}
log("banks:", len(banks), "pairs:", bankmap["pairs"])

# ---------------------------------------------------------------- outlines
outline_files = sorted(glob.glob(os.path.join(W, "mission2", "out", "outlines", "*.outline.json")))
log("outlines:", len(outline_files))

def outline_txt(o):
    parts = []
    for st in o["states"]:
        lab = ("~" if st["structural"] else "") + (st["name"] if st["name"] else st["hash"])
        if st.get("pos"):
            lab += st["pos"]
        s = "%s(%d)" % (lab, st["records"])
        if len(st["bands"]) > 1:
            s += " b[" + ",".join(str(b) for b in st["bands"]) + "]"
        if st["entities"]:
            s += " e=%d" % st["entities"]
        parts.append(s)
    return " -> ".join(parts)

# ---------------------------------------------------------------- vocabulary overlay
# Layer C: the cutscene-state family grammar from BRUTE.md 4b (work\brute\hits_family.txt),
# plus BRUTE.md 4a names found by dictionary intersection.  Applied as a *re-labelling only*:
# no outline byte is re-decoded, the hash and the structural flag stay the outline json's.
FAM = os.path.join(W, "brute", "hits_family.txt")
fam_by = collections.defaultdict(list)
if os.path.exists(FAM):
    for ln in open(FAM, encoding="utf-8", errors="replace"):
        q = ln.rstrip("\n").split("\t")
        if len(q) < 3:
            continue
        h = q[0].strip().lower()
        if len(h) != 8:
            continue
        fam_by[h].append((int(q[1]), q[2]))
OVERLAY = {}
for h, v in fam_by.items():
    names = sorted({n for _, n in v}, key=lambda s: (len(s), s))
    OVERLAY[h] = {"name": names[0], "occ": max(o for o, _ in v),
                  "tier": "C:family", "variants": names}
# BRUTE.md 4a names not produced by the grammar (manual table, kept separate)
for h, nm, ev in [
    ("c7530b3c", "disrupt", "BRUTE.md 4a: entry 9 of work/arch/dict/d*_names.tsv, literal in two docs"),
]:
    OVERLAY.setdefault(h, {"name": nm, "occ": 104, "tier": "A:manual", "variants": [nm],
                           "evidence": ev})
log("vocabulary overlay:", len(OVERLAY), "hashes")

# BRUTE.md 6: position-only readings for the four hashes that stay unnamed.  These are NOT names.
POS = {
    "320488a8": "\u27e81/3\u27e9",   # entry state of a 3-state machine
    "43b1d4af": "\u27e82/3\u27e9",   # mid state of the same machine
    "b7359923": "\u27e8loop\u27e9",  # only gameplay state between two cutscene states
    "3aff3ce4": "\u27e8pre-HOPOUT\u27e9",
}
POSNOTE = {
    "320488a8": "state 1 of 3, the entry state; always paired with 43b1d4af; g0380-g0387 (BRUTE.md 6)",
    "43b1d4af": "state 2 of 3, the mid state of the same machine; g0380-g0387 (BRUTE.md 6)",
    "b7359923": "the single looping gameplay state between Outro and INTRO; g0371-g0379 (BRUTE.md 6)",
    "3aff3ce4": "state 3 of 5, immediately before HOPOUT - the 'get the car into position' beat; g1096-g1126 (BRUTE.md 6)",
}
vocab_stats = collections.Counter()

# phase classifier: same keyword rules and precedence as work/mission2/out/_phases.json,
# re-applied here so that newly named states also get a phase tag.
_PH = jload(os.path.join(W, "mission2", "out", "_phases.json"))
RULES = _PH["rules"]; PREC = _PH["precedence"]

def classify(name):
    if not name:
        return None
    ln = name.lower()
    for ph in PREC:
        for kw in RULES.get(ph, []):
            if kw in ln:
                return ph
    return None


OUTL = {}
BEFORE = {"named_real_states": 0, "real_states": 0, "named_states": 0,
          "records_named": 0, "records_total": 0}
for p in outline_files:
    o = jload(p)
    fid = o["file"].replace(".json", "")
    o["id"] = fid
    BEFORE["named_real_states"] += o["named_real_states"]
    BEFORE["real_states"] += o["real_states"]
    BEFORE["named_states"] += o["named_states"]
    BEFORE["records_total"] += o["records"]
    BEFORE["records_named"] += sum(st["records"] for st in o["states"] if st["name"])
    for st in o["states"]:
        st["name_src"] = "ship" if st["name"] else "none"
        st["pos"] = POS.get(st["hash"])
        st["phase_before"] = classify(st["name"])
        if st["name"] is None and st["hash"] in OVERLAY:
            st["name"] = OVERLAY[st["hash"]]["name"]
            st["name_src"] = OVERLAY[st["hash"]]["tier"]
            vocab_stats["relabelled"] += 1
            if st["structural"]:
                st["structural"] = False
                vocab_stats["reclassified_from_structural"] += 1
                o.setdefault("reclassified", []).append(st["hash"])
        if st["name"] is None and st["pos"]:
            vocab_stats["position_only"] += 1
        st["phase"] = classify(st["name"])
        if st["phase"] != st["phase_before"] and st["phase"]:
            vocab_stats["phases_gained"] += 1
        vocab_stats["named_after"] += 1 if st["name"] else 0
    o["phases_before"] = [st["phase_before"] for st in o["states"]]
    o["phases"] = [st["phase"] for st in o["states"]]

    o["named_states"] = sum(1 for st in o["states"] if st["name"])
    o["real_states"] = sum(1 for st in o["states"] if not st["structural"])
    o["named_real_states"] = sum(1 for st in o["states"] if st["name"] and not st["structural"])
    o["named_fraction"] = (round(o["named_real_states"] / o["real_states"], 4) if o["real_states"] else None)
    o["records"] = sum(st["records"] for st in o["states"])
    o["entities"] = sum(st["entities"] for st in o["states"])
    o["state_count"] = len(o["states"])
    o["txt"] = outline_txt(o)
    o["group"] = "g" + fid[1:5]
    o["sig"] = "|".join(sorted(st["hash"] for st in o["states"]))
    o["named_sig"] = "|".join(sorted(st["name"] for st in o["states"] if st["name"]))
    o["structural_only"] = all(st["structural"] for st in o["states"])
    OUTL[fid] = o
log("outlines loaded:", len(OUTL), "| vocab", dict(vocab_stats))


# ---------------------------------------------------------------- clusters of identical state sets
cl = collections.defaultdict(list)
for fid, o in OUTL.items():
    cl[o["sig"]].append(fid)
clusters = sorted(([k, v] for k, v in cl.items() if len(v) > 1), key=lambda x: -len(x[1]))
log("identical-state-set clusters (size>1):", len(clusters),
    "files in them:", sum(len(v) for _, v in clusters))

# ---------------------------------------------------------------- bank joins
bank_by_prefix = collections.defaultdict(list)
for bname, b in banks.items():
    # documented pattern (MANIFEST.md 5): <MISSIONID>AU_<...>
    idx = bname.find("AU_")
    pref = bname[:idx] if idx > 0 else None
    bank_by_prefix[pref].append(bname)

def banks_for_mission(mid):
    out = []
    for pref, bl in bank_by_prefix.items():
        if pref is None:
            continue
        if pref == mid or pref.startswith(mid + "_") or mid.startswith(pref + "_"):
            out.extend(bl)
    # exact-prefix wins: prefer exact
    exact = bank_by_prefix.get(mid, [])
    return sorted(set(exact)), sorted(set(out) - set(exact))

# ---------------------------------------------------------------- mission records
def group_of(mid):
    if "_" in mid:
        return mid.split("_")[0]
    return "misc"

pidx = jload(os.path.join(W, "mission", "out", "_per_file.json"))
per_file = {r["file"].replace(".json", ""): r for r in pidx}

MISS = []
for mid in missions:
    b = bundles.get(mid, {})
    rows = mmap.get(mid, [])
    docmap = collections.Counter(r[3] for r in rows if len(r) > 3)
    exact, approx = banks_for_mission(mid)
    cset = sorted({bname for bname in b.get("cutscene_audio_banks", [])})
    M = {
        "mission_id": mid,
        "group": group_of(mid),
        "description_key": b.get("description_key"),
        "grid_texture": b.get("grid_texture"),
        "in_cmissions": b.get("in_cmissions_list", False),
        "docs": [{"archive": r[0], "size": r[1], "doc": r[2], "kind": r[3]} for r in rows if len(r) > 3],
        "doc_kinds": dict(docmap),
        "weapon_loadouts": b.get("weapon_loadouts", []),
        "vehicle_tint_presets": b.get("vehicle_tint_presets", []),
        "lighting_modifiers": b.get("lighting_modifiers", []),
        "manifest_content_sets": b.get("manifest_content_sets", []),
        "manifest_content_files": b.get("manifest_content_files", []),
        "bundled_cutscene_banks": cset,
        "banks_exact_prefix": exact,
        "banks_loose_prefix": approx,
        "evidence": b.get("evidence", {}),
        "outline_id": None,
        "outline_binding": None,
        "chapter": None,
    }
    import re as _re
    _g = M["grid_texture"] or ""
    _mm = _re.search(r"CH(\d+)", _g)
    if _mm:
        M["chapter"] = int(_mm.group(1))
    # asset stem: the id the progression/asset tables actually use for this mission.
    # string-level only (grid texture + description key), so it is a naming join, not a behaviour join.
    _sm = _re.match(r"^GRID_SML_L_(?:CH\d+_)?(.+)$", _g)
    M["asset_stem"] = _sm.group(1) if _sm else None
    _dm = _re.match(r"^PROG_(.+)_DESC_REPLAY$", M["description_key"] or "")
    M["desc_stem"] = _dm.group(1) if _dm else None
    MISS.append(M)

# ---------------------------------------------------------------- the one proven binding
# MISSION.md 7: joaat("robbergetawaydriverprep") is a record key in g1730 only.
BINDING = {"mission_id": "robbergetawaydriverprep", "outline_id": "g1730_045AE000",
           "kind": "record key", "provenance": "proven", 
           "note": "joaat(robbergetawaydriverprep)=0x6a131547 appears as a record key 8x in g1730 and in no other group file (MISSION.md 7)"}
for M in MISS:
    if M["mission_id"] == BINDING["mission_id"]:
        M["outline_id"] = BINDING["outline_id"]
        M["outline_binding"] = "proven:record-key"

# ---------------------------------------------------------------- runtime placements (8 files)
place = {}
for p in sorted(glob.glob(os.path.join(W, "missionrt", "missions", "g*.json"))):
    fid = os.path.basename(p).replace(".json", "")
    d = jload(p)
    m = d.get("mission", {})
    ents = {}
    for st in m.get("states", []):
        for r in st.get("records", []):
            for e in (r.get("entities") or []):
                ents[e.get("pool_offset")] = e
    pos = [e["pos"] for e in ents.values() if e.get("pos")]
    bb = None
    if pos:
        bb = {"min": [min(p[i] for p in pos) for i in range(3)],
              "max": [max(p[i] for p in pos) for i in range(3)]}
    arch = collections.Counter(e.get("archetype") for e in ents.values() if e.get("archetype"))
    place[fid] = {"records": m.get("summary", {}).get("records"),
                  "entities": len(ents), "bbox": bb,
                  "archetypes": len(arch),
                  "top_archetypes": arch.most_common(8),
                  "states": m.get("summary", {}).get("state_hashes")}
    log("placements", fid, len(ents))

# archetype hash -> name
arch_names = {}
ap = os.path.join(W, "arch", "out", "bindings.json")
if os.path.exists(ap):
    for r in jload(ap)["bindings"]:
        h = (r.get("archetype_hash") or "").lower().replace("0x", "").lstrip("0")
        if r.get("name"):
            arch_names[h.zfill(8)] = r["name"]
log("archetype names:", len(arch_names))
for fid, pl in place.items():
    pl["top_archetypes_named"] = [[a, arch_names.get(a.lower().replace("0x", "").zfill(8)), n]
                                  for a, n in pl["top_archetypes"]]

# ---------------------------------------------------------------- stats
shape = jload(os.path.join(W, "mission2", "out", "_corpus_shape.json"))
phases = jload(os.path.join(W, "mission2", "out", "_phases.json"))
res2 = jload(os.path.join(W, "mission2", "out", "_resolution2.json"))
rank = jload(os.path.join(W, "mission2", "out", "_ranking.json"))

VOCAB = {
    "before": BEFORE,
    "after": {"named_real_states": sum(o["named_real_states"] for o in OUTL.values()),
              "real_states": sum(o["real_states"] for o in OUTL.values()),
              "named_states": sum(o["named_states"] for o in OUTL.values()),
              "records_named": sum(sum(st["records"] for st in o["states"] if st["name"])
                                   for o in OUTL.values()),
              "records_total": sum(o["records"] for o in OUTL.values())},
    "overlay_hashes": len(OVERLAY),
    "overlay_used_in_outlines": len({st["hash"] for o in OUTL.values() for st in o["states"]
                                     if st.get("name_src", "").startswith(("C:", "A:"))}),
    "relabelled_state_slots": vocab_stats["relabelled"],
    "reclassified_from_structural": vocab_stats["reclassified_from_structural"],
    "position_only_states": vocab_stats["position_only"],
    "collision_budget": "family grammar: 2,646,173 candidates x 5,861 targets / 2^32 = 3.6 expected lucky preimages (BRUTE.md 4b)",
}
VOCAB["before"]["named_real_pct"] = round(100.0 * BEFORE["named_real_states"] / BEFORE["real_states"], 2)
VOCAB["after"]["named_real_pct"] = round(100.0 * VOCAB["after"]["named_real_states"] / VOCAB["after"]["real_states"], 2)
VOCAB["before"]["records_named_pct"] = round(100.0 * BEFORE["records_named"] / BEFORE["records_total"], 2)
VOCAB["after"]["records_named_pct"] = round(100.0 * VOCAB["after"]["records_named"] / VOCAB["after"]["records_total"], 2)
log("vocab before/after:", VOCAB["before"]["named_real_pct"], "->", VOCAB["after"]["named_real_pct"], "%")

json.dump(MISS, open(os.path.join(OUT, "_missions.json"), "w", encoding="utf-8"), indent=1)
json.dump(OVERLAY, open(os.path.join(OUT, "_vocab_overlay.json"), "w", encoding="utf-8"), indent=1)
json.dump({"pos": POS, "posnote": POSNOTE, "vocab": VOCAB},
          open(os.path.join(OUT, "_posread.json"), "w", encoding="utf-8"), indent=1)

json.dump({fid: {k: v for k, v in o.items()} for fid, o in OUTL.items()},
          open(os.path.join(OUT, "_outlines.json"), "w", encoding="utf-8"))
json.dump([{"sig": k, "n": len(v), "files": v} for k, v in clusters],
          open(os.path.join(OUT, "_clusters.json"), "w", encoding="utf-8"), indent=1)
json.dump(place, open(os.path.join(OUT, "_placements.json"), "w", encoding="utf-8"), indent=1)
json.dump({"shape": shape, "phases": phases, "resolution": res2,
           "clusters_total": len(clusters),
           "files_in_clusters": sum(len(v) for _, v in clusters),
           "bank_index_capacity": bankmap["audio_index"],
           "vocab": VOCAB},
          open(os.path.join(OUT, "_stats.json"), "w", encoding="utf-8"), indent=1)

log("wrote index files")
