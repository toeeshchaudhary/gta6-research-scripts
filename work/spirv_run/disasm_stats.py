"""Summarise a disassembly directory: per shader, per stage instruction counts and invalid-word counts.

usage: python disasm_stats.py <disasm dir> <index.json> [--json out.json]
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

HDR = re.compile(r"^;\s*(\S+)\s+code 0x([0-9a-f]+)\.\.0x([0-9a-f]+) \((\w+)\), (\w+), (\d+) invalid words")
INS = re.compile(r"^\t(\S+)")


def main():
    d, idxp = sys.argv[1], sys.argv[2]
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    stage = {}
    for e in json.load(open(idxp, encoding="utf-8")):
        stage[os.path.splitext(os.path.basename(e["file"]))[0]] = e["stage"]
    rows = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".s"):
            continue
        lines = open(os.path.join(d, f), encoding="utf-8", errors="replace").read().splitlines()
        m = HDR.match(lines[0]) if lines else None
        n = 0
        for ln in lines[1:]:
            if ln.startswith("; ---"):
                break
            if INS.match(ln):
                n += 1
        name = f[:-2]
        rows.append({"name": name, "stage": stage.get(name, "?"), "insns": n,
                     "start": int(m.group(2), 16) if m else None,
                     "end": int(m.group(3), 16) if m else None,
                     "how": m.group(4) if m else None, "invalid": int(m.group(6)) if m else None})
    by = defaultdict(lambda: {"n": 0, "clean": 0, "inv_words": 0, "insns": 0, "bytes": 0, "sheets": []})
    for r in rows:
        b = by[r["stage"]]
        b["n"] += 1
        b["clean"] += r["invalid"] == 0
        b["inv_words"] += r["invalid"] or 0
        b["insns"] += r["insns"]
        b["bytes"] += (r["end"] or 0) - (r["start"] or 0)
        b["sheets"].append(r)
    tot = {"n": 0, "clean": 0, "insns": 0, "inv": 0}
    for s in sorted(by):
        b = by[s]
        tot["n"] += b["n"]
        tot["clean"] += b["clean"]
        tot["insns"] += b["insns"]
        tot["inv"] += b["inv_words"]
        print(f"{s:3} n={b['n']:3} clean={b['clean']:3} invalid_words={b['inv_words']:4} "
              f"insns={b['insns']:7} mean_insns/shader={b['insns']/b['n']:8.1f} "
              f"mean_bytes={b['bytes']/b['n']:8.1f}")
    print(f"ALL n={tot['n']} clean={tot['clean']} invalid_words={tot['inv']} insns={tot['insns']} "
          f"mean={tot['insns']/max(1,tot['n']):.1f} insns/shader")
    for r in rows:
        if r["invalid"]:
            print(f"  invalid: {r['name']} stage={r['stage']} words={r['invalid']} insns={r['insns']} loose_words={((r['end'] or 0)-(r['start'] or 0))//4-r['insns']}")
    if out:
        json.dump({"per_stage": {k: {kk: vv for kk, vv in v.items() if kk != "sheets"} for k, v in by.items()},
                   "shaders": rows}, open(out, "w", encoding="utf-8"), indent=1)
        print("wrote", out)


if __name__ == "__main__":
    sys.exit(main())

