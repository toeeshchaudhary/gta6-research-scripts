"""Analysis pass over the emitted JSON: structural statistics + honest top-unresolved."""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_min as L

OUT = os.path.join(L.WS, "work", "mission", "out")


def structural(h):
    """True for words that are not plausible joaat identifiers."""
    if h in (0x80808080, 0xAAAAAAAA, 0xFFFFFFFF, 0x70707070, 0x71717171):
        return True
    if h < 0x10000:
        return True
    # packed (u16 kind, u16 value) words: second byte is always zero
    if (h & 0xFF00) == 0:
        return True
    b = h.to_bytes(4, "little")
    if len(set(b)) == 1:
        return True
    # floats in the -3000..3000 range all start 0xc5xx / 0x44xx..0x40xx
    if (h >> 24) in (0xC5, 0xC4, 0xC6) and (h & 0xFF) < 0x20:
        return True
    return False


def main():
    src = L.build_dicts()
    dic, _ = L.merged(src)
    keyhits = collections.Counter()
    blobhits = collections.Counter()
    kindcnt = collections.Counter()
    files_with_records = 0
    per_file = []
    total_recs = 0
    chunkroles = collections.Counter()
    tags = collections.Counter()
    prefix = collections.Counter()

    for fn in sorted(os.listdir(OUT)):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        d = json.load(open(os.path.join(OUT, fn), encoding="utf-8"))
        nrec = 0
        keys = set()
        for ch in d["chunks"]:
            chunkroles[ch["role"]] += 1
            tags[ch["tag"]] += 1
            if ch["role"] == "records":
                nrec += len(ch.get("records", []))
                for r in ch.get("records", []):
                    keyhits[int(r["key"],16)] += 1
                    if r["attr"]:
                        keyhits[int(r["attr"],16)] += 1
                    kindcnt[r["kind"]] += 1
                    keys.add(int(r["key"],16))
        if nrec:
            files_with_records += 1
        total_recs += nrec
        per_file.append({"file": fn, "records": nrec,
                         "distinct_keys": len(keys),
                         "chunks": len(d["chunks"]),
                         "len": d["len"],
                         "missions": sorted({dic[k] for k in keys
                                             if k in src["mission_ids"]}),
                         "named_keys": sorted({dic[k] for k in keys
                                               if k in dic and k not in
                                               src["mission_ids"]})[:12]})
    unres = [(h, c) for h, c in keyhits.most_common(4000)
             if h not in dic and not structural(h)]
    out = {
        "files": len(per_file),
        "files_with_records": files_with_records,
        "total_records": total_recs,
        "roles": dict(chunkroles),
        "tags": dict(tags.most_common()),
        "distinct_record_hashes": len(keyhits),
        "resolved_record_hashes": sum(1 for h in keyhits if h in dic),
        "resolved_record_rate_pct": round(
            100.0 * sum(1 for h in keyhits if h in dic) / max(1, len(keyhits)), 3),
        "kind_histogram": dict(kindcnt.most_common(30)),
        "top_unresolved_identifier": [{"hash": "%08x" % h, "count": c}
                                      for h, c in unres[:10]],
    }
    json.dump(out, open(os.path.join(OUT, "_analysis.json"), "w", encoding="utf-8"),
              indent=1)
    json.dump(per_file, open(os.path.join(OUT, "_per_file.json"), "w",
                             encoding="utf-8"), indent=0)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
