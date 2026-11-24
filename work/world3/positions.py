"""Distinct-position / degeneracy statistics for the complete scan.
usage: python -I positions.py <scene.json> <report.json>
"""
import json
import sys

scene, report = sys.argv[1], sys.argv[2]
inst = json.load(open(scene, encoding="utf-8"))["instances"]
rep = {"instances": len(inst)}
for cls in ("S", "M"):
    rows = [i for i in inst if i.get("class") == cls]
    p2 = {(round(i["pos"][0], 2), round(i["pos"][1], 2), round(i["pos"][2], 2)) for i in rows}
    p3 = {(round(i["pos"][0], 3), round(i["pos"][1], 3), round(i["pos"][2], 3)) for i in rows}
    rep[cls] = {
        "instances": len(rows),
        "distinct_2dp": len(p2),
        "unique_2dp_frac": round(len(p2) / len(rows), 4) if rows else 0,
        "distinct_3dp": len(p3),
        "at_origin": sum(1 for i in rows if i["pos"] == [0, 0, 0] or all(abs(v) < 1e-6 for v in i["pos"])),
        "most_repeated_2dp": sorted(((p, n) for p, n in
            __import__("collections").Counter(
                (round(i["pos"][0], 2), round(i["pos"][1], 2), round(i["pos"][2], 2)) for i in rows).items()),
            key=lambda kv: -kv[1])[:5],
    }
json.dump(rep, open(report, "w", encoding="utf-8"), indent=1, default=str)
print(json.dumps(rep, indent=1, default=str))
