"""Shot builder that selects by real geometry, not by instance count.

For every bound entity in a box around a centre it measures the OBJ's actual height and footprint
(cheap for the few hundred models involved), then keeps the district's building-sized geometry first
and fills the triangle budget with the rest. Nothing about the placement is changed: position,
conjugated quaternion and the game's scale go straight through.

Usage: python -I shot_real.py --center -150,-1050 --radius 300 --out out\shot_a.json
"""
import argparse
import collections
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def bbox(path):
    lo = [1e30, 1e30, 1e30]
    hi = [-1e30, -1e30, -1e30]
    with open(path, "rb") as f:
        for line in f:
            if line[:2] != b"v ":
                continue
            t = line.split()
            v = (float(t[1]), float(t[2]), float(t[3]))
            for k in range(3):
                if v[k] < lo[k]:
                    lo[k] = v[k]
                if v[k] > hi[k]:
                    hi[k] = v[k]
    return lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=os.path.join(HERE, "out", "scene_city_bound.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--center", required=True)
    ap.add_argument("--radius", type=float, default=300.0)
    ap.add_argument("--max-inst", type=int, default=3000)
    ap.add_argument("--models", type=int, default=260)
    ap.add_argument("--budget", type=int, default=9000000)
    ap.add_argument("--model-tris", type=int, default=400000)
    a = ap.parse_args()
    cx, cy = (float(v) for v in a.center.split(","))

    inst = json.load(open(a.src, encoding="utf-8"))["instances"]
    arch = json.load(open(os.path.join(ROOT, "work", "draw", "out", "arch_model.json"), encoding="utf-8"))
    tri = {b["obj_file"]: b["tris"] for b in arch["bindings"]}
    near = [i for i in inst if abs(i["pos"][0] - cx) <= a.radius and abs(i["pos"][1] - cy) <= a.radius]
    models = sorted({i["model"] for i in near})
    print(f"{len(near)} bound instances, {len(models)} distinct models in the box")

    size = {}
    for m in models:
        if tri.get(m, 0) > a.model_tris:
            size[m] = (0.0, 0.0)
            continue
        try:
            lo, hi = bbox(m)
            size[m] = (hi[2] - lo[2], max(hi[0] - lo[0], hi[1] - lo[1]))
        except (OSError, ValueError, IndexError):
            size[m] = (0.0, 0.0)
    tall = sorted((m for m in models if size[m][0] >= 12.0), key=lambda m: -size[m][0])
    print(f"{len(tall)} models at least 12 m tall, tallest {size[tall[0]][0]:.1f} m" if tall else "no tall model")

    used, tris = [], 0
    for m in tall + [m for m in models if m not in set(tall)]:
        t = tri.get(m, 0)
        if t > a.model_tris or tris + t > a.budget or len(used) >= a.models:
            continue
        used.append(m)
        tris += t
    mset = set(used)
    keep = [i for i in near if i["model"] in mset]
    keep.sort(key=lambda i: -size.get(i["model"], (0, 0))[0])
    keep = keep[: a.max_inst]

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"note": f"real CEntityDef placement around ({cx:g},{cy:g}), height-selected",
                   "instances": keep}, f, separators=(",", ":"))
    zs = [i["pos"][2] for i in keep]
    print(f"wrote {a.out}: {len(keep)} instances, {len(mset)} models, {tris} tris, "
          f"z {min(zs):.1f}..{max(zs):.1f}")
    nm = collections.Counter(i["name"] for i in keep)
    print("top:", ", ".join(f"{n}x{c}" for n, c in nm.most_common(8)))


if __name__ == "__main__":
    main()
