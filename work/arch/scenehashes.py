"""Extract distinct archetype hashes + instance frequency from a scene file.

Usage: python -I scenehashes.py scene.json out.tsv
"""
import json
import sys
from collections import Counter


def main():
    scene, out = sys.argv[1], sys.argv[2]
    d = json.load(open(scene, encoding="utf-8"))
    inst = d["instances"] if isinstance(d, dict) else d
    c = Counter()
    for r in inst:
        h = r.get("hash")
        c[h] += 1
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for h, n in c.most_common():
            f.write(f"{h}\t{n}\n")
    print(f"{scene}: {len(inst)} instances, {len(c)} distinct hashes -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
