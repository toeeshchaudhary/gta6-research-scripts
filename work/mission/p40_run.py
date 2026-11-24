"""Driver v2: classify every chunk by record-template validity, decode real tables.

A chunk is a *record table* when >=90% of its 32-byte slots after the 16-byte header satisfy
d[1]==0 and d[5]==0 and d[7]==0 (the four zero separator dwords of the template). Everything
else is a value blob. Only table chunks produce records; blobs are hashed for statistics.
"""
import collections
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_min as L

OUT = os.path.join(L.WS, "work", "mission", "out")
PROG = os.path.join(L.WS, "work", "mission", "PROGRESS.md")
MIN_VALID = 0.9


def log(m):
    with open(PROG, "a", encoding="utf-8") as f:
        f.write(m + "\n")


def slots_ok(b, off, size):
    total = 0
    good = 0
    i = off + 16
    end = off + size - 15
    while i < end:
        d = struct.unpack_from("<8I", b, i)
        total += 1
        if d[1] == 0 and d[7] == 0 and d[0] != 0 and d[5] < 0x10000:
            good += 1
        i += 32
    return (good / total if total else 0.0), total


def main():
    os.makedirs(OUT, exist_ok=True)
    src = L.build_dicts()
    dic, origin = L.merged(src)
    log("## dict " + json.dumps({k: len(v) for k, v in src.items()}))

    files = sorted(f for f in os.listdir(L.GROUPS) if f.endswith(".bin"))
    stats = collections.Counter()
    hash_hits = collections.Counter()
    per_file = []

    for fn in files:
        b = open(os.path.join(L.GROUPS, fn), "rb").read()
        c = L.parse_container(b)
        if c is None:
            stats["not_psin"] += 1
            continue
        stats["psin"] += 1
        chunks = c["chunks"]
        pools = {}
        for j, ch in enumerate(chunks):
            for k in range(j + 1, len(chunks)):
                if L.is_pool(chunks[k]["tag"]):
                    pools[ch["tag"]] = chunks[k]
                    break
        doc = {"file": fn, "len": len(b),
               "header": {"version": c["version"], "desc_count": len(chunks),
                          "header_len": c["header_len"],
                          "sum_sizes": c["covered"] - c["header_len"],
                          "trailing": c["file_len"] - c["covered"]},
               "chunks": []}
        for ch in chunks:
            val, total = slots_ok(b, ch["off"], ch["size"])
            cd = {"tag": "%08x" % ch["tag"], "size": ch["size"], "off": ch["off"],
                  "slots": total, "validity": round(val, 3)}
            lead = b[ch["off"]:ch["off"] + 4]
            cd["hdr_word"] = lead.hex()
            if val >= MIN_VALID:
                cd["role"] = "records"
                stats["rec_chunks"] += 1
                pool = pools.get(ch["tag"])
                recs = L.parse_records(b, ch["off"], ch["size"])
                out = []
                for r in recs:
                    hash_hits[r["key"]] += 1
                    if r["attr"]:
                        hash_hits[r["attr"]] += 1
                    rj = {"at": r["at"], "key": "%08x" % r["key"],
                          "key_name": dic.get(r["key"]) if r["key"] > 0xFFFF else None,
                          "attr": "%08x" % r["attr"] if r["attr"] else None,
                          "attr_name": dic.get(r["attr"]) if r["attr"] else None,
                          "kind": r["kind"], "offset": r["offset"],
                          "count": r["count"], "count_dup": r["count_dup"], "row": r["row"],
                          "pool": ("%08x" % pool["tag"]) if pool else None}
                    if pool:
                        vals = L.values_at(b, pool["off"], r["offset"],
                                           min(r["count"], 32))
                        rj["values"] = [v["raw"] for v in vals]
                        fl = [v["float"] for v in vals]
                        if any(x is not None for x in fl):
                            rj["floats"] = fl
                    out.append(rj)
                cd["records"] = out
            else:
                cd["role"] = "blob"
                stats["blob_chunks"] += 1
                # blob contents: count leading hashes and floats for statistics
                n_h = 0
                n_f = 0
                i = ch["off"]
                end = ch["off"] + ch["size"] - 3
                while i < end:
                    v = struct.unpack_from("<I", b, i)[0]
                    f = struct.unpack_from("<f", b, i)[0]
                    if math.isfinite(f) and (f == 0 or 1e-4 < abs(f) < 1e5):
                        n_f += 1
                    elif v > 0xFFFF:
                        n_h += 1
                        hash_hits[v] += 1
                    i += 4
                cd["float_share"] = round(n_f / max(1, n_f + n_h), 3)
            doc["chunks"].append(cd)
        with open(os.path.join(OUT, fn.replace(".bin", ".json")), "w",
                  encoding="utf-8") as f:
            json.dump(doc, f, separators=(",", ":"))
        per_file.append({"file": fn, "len": len(b), "chunks": len(chunks),
                         "rec_chunks": sum(1 for ch in doc["chunks"]
                                           if ch["role"] == "records")})

    with open(os.path.join(OUT, "_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "files": per_file}, f, indent=1)

    allh = set(hash_hits)
    rep = {"distinct_hashes": len(allh), "occurrences": sum(hash_hits.values())}
    for name, d in src.items():
        hits = sum(1 for h in allh if h in d)
        rep[name] = {"dict_size": len(d), "resolved": hits,
                     "rate_pct": round(100.0 * hits / max(1, len(allh)), 4)}
    tot = sum(1 for h in allh if h in dic)
    rep["merged"] = {"dict_size": len(dic), "resolved": tot,
                     "rate_pct": round(100.0 * tot / max(1, len(allh)), 4)}
    rep["top_unresolved"] = [
        {"hash": "%08x" % h, "count": c} for h, c in hash_hits.most_common(200)
        if h not in dic][:10]
    with open(os.path.join(OUT, "_resolution.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    log("DONE files=%d recchunks=%d distinct=%d resolved=%d" %
        (len(files), stats["rec_chunks"], len(allh), tot))
    print(json.dumps({k: v for k, v in rep.items() if k != "top_unresolved"}, indent=1))


if __name__ == "__main__":
    main()
