"""Per-stage table for the graphics corpus (vs/ps/ms/gs) from the completed row logs.

Dedupes by shader name (a shader may be re-run in several logs), keeping the best outcome, and prints
attempted / disassembled / translated / spirv-as ok / spirv-val 1.2 ok / spirv-val 1.3 ok with percentages.
"""
import collections
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def rank(r):
    if r.get("val13_ok") or r.get("val_ok"):
        return 4
    if r.get("as_ok"):
        return 3
    if r.get("spirv_ok"):
        return 2
    return 1


def main():
    rows = {}
    for f in sorted(glob.glob(os.path.join(HERE, "logs*", "rows*.jsonl"))):
        if os.path.basename(os.path.dirname(f)) == "logs_cs":
            continue
        for l in open(f, encoding="utf-8", errors="replace"):
            l = l.strip()
            if not l:
                continue
            try:
                r = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            n = r.get("name")
            st = r.get("stage")
            if not n or st not in ("vs", "ps", "ms", "gs"):
                continue
            if n not in rows or rank(r) > rank(rows[n]):
                rows[n] = r
    by = collections.defaultdict(lambda: collections.Counter())
    for n, r in rows.items():
        c = by[r["stage"]]
        c["attempted"] += 1
        c["spirv"] += bool(r.get("spirv_ok"))
        c["as"] += bool(r.get("as_ok"))
        c["val"] += bool(r.get("val_ok"))
        c["val13"] += bool(r.get("val13_ok"))
        c["err"] += bool(r.get("error"))
        c["wave64"] += bool(r.get("wave64"))
        c["insns"] += r.get("insns") or 0
    tot = collections.Counter()
    for st in ("vs", "ps", "ms", "gs"):
        if st not in by:
            continue
        c = by[st]
        tot |= c
        print("%-3s attempted=%5d spirv=%5d (%.1f%%) val=%5d (%.1f%%) val13=%5d (%.1f%%) err=%4d insns=%d"
              % (st, c["attempted"], c["spirv"], 100.0 * c["spirv"] / max(1, c["attempted"]),
                 c["val"], 100.0 * c["val"] / max(1, c["attempted"]),
                 c["val13"], 100.0 * c["val13"] / max(1, c["attempted"]), c["err"], c["insns"]))
    print("-" * 100)
    print("ALL attempted=%d spirv=%d (%.1f%%) val=%d (%.1f%%) val13=%d (%.1f%%)"
          % (tot["attempted"], tot["spirv"], 100.0 * tot["spirv"] / max(1, tot["attempted"]),
             tot["val"], 100.0 * tot["val"] / max(1, tot["attempted"]),
             tot["val13"], 100.0 * tot["val13"] / max(1, tot["attempted"])))
    errs = collections.Counter()
    for n, r in rows.items():
        e = r.get("error")
        if e:
            errs[e.split("\n")[0][:100]] += 1
    print("\ntop graphics error strings:")
    for e, c in errs.most_common(15):
        print("%6d  %s" % (c, e))


if __name__ == "__main__":
    main()
