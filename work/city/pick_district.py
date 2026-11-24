"""Pick a real district to render: measure the actual geometry height of the placed tile models.

The entity row gives position/rotation/scale but not size, so the only way to know whether a district
is downtown (tall buildings) or flat terrain is to open the OBJs we bound there. This measures the
bound tile models inside a few candidate boxes and reports which box has the tallest geometry.

Usage: python -I pick_district.py --centers "-150,-1050;150,-1050;-1200,-1200" --radius 230
"""
import argparse
import collections
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TILE = re.compile(r"^[ns][0-9]{2}_[we][0-9]{2}_[0-9]{3}_hd$")


def height(path):
    lo, hi = 1e30, -1e30
    with open(path, "rb") as f:
        for line in f:
            if line[:2] != b"v ":
                continue
            t = line.split()
            z = float(t[3])
            if z < lo:
                lo = z
            if z > hi:
                hi = z
    return hi - lo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--centers", required=True, help="x,y;x,y;...")
    ap.add_argument("--radius", type=float, default=230.0)
    ap.add_argument("--min-tris", type=int, default=3000)
    ap.add_argument("--in", dest="src", default=os.path.join(HERE, "out", "scene_city_bound.json"))
    a = ap.parse_args()
    inst = json.load(open(a.src, encoding="utf-8"))["instances"]
    arch = json.load(open(os.path.join(HERE, "..", "..", "work", "draw", "out", "arch_model.json"),
                          encoding="utf-8"))["bindings"]
    tri = {b["obj_file"]: b["tris"] for b in arch}
    cache = {}
    out = []
    for spec in a.centers.split(";"):
        cx, cy = (float(v) for v in spec.split(","))
        near = [i for i in inst if abs(i["pos"][0] - cx) <= a.radius and abs(i["pos"][1] - cy) <= a.radius]
        tiles = {i["model"]: i for i in near if TILE.match(i["name"]) or tri.get(i["model"], 0) >= a.min_tris}
        hs = []
        for m, i in tiles.items():
            if m not in cache:
                try:
                    cache[m] = height(m)
                except (OSError, ValueError, IndexError):
                    cache[m] = 0.0
            hs.append((cache[m], m, i["name"]))
        hs.sort(reverse=True)
        tall = [h for h in hs if h[0] > 15]
        out.append({"center": spec, "instances": len(near), "models": len(tiles),
                    "tall_models": len(tall), "tall_instances": sum(
                        1 for i in near if i["model"] in {h[1] for h in tall}),
                    "max_h": round(hs[0][0], 1) if hs else 0,
                    "sum_tall_h": round(sum(h[0] for h in tall), 1),
                    "top": [(round(h[0], 1), h[2]) for h in hs[:4]]})
        print(json.dumps(out[-1]))
    out.sort(key=lambda r: -r["sum_tall_h"])
    print("\nbest:")
    for r in out[:4]:
        print(" ", json.dumps(r))
    with open(os.path.join(HERE, "out", "districts.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
