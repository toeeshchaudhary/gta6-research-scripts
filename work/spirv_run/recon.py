"""Reconcile every rows.part*.jsonl from both log dirs into one authoritative tally.

Dedupe rule: a shader name may appear in several row files (retries, second corpus run, patched
reruns).  We keep the *best* row, ordered by (val_ok, val13_ok, as_ok, spirv_ok), and record how
many duplicate records were collapsed, so nothing is silently double counted.

usage: python recon.py [--json out.json]
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
STAGES = ("vs", "ps", "ms", "gs", "cs")

SOURCES = [
    os.path.join(HERE, "logs_s2", "rows.part*.jsonl"),
    os.path.join(HERE, "logs", "rows.part*.jsonl"),
]


def rank(r):
    return (bool(r.get("val_ok")), bool(r.get("val13_ok")),
            bool(r.get("as_ok")), bool(r.get("spirv_ok")))


def main():
    out = None
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]

    best = {}
    per_file = {}
    dup = Counter()
    unparsable = Counter()
    files = []
    for pat in SOURCES:
        files.extend(sorted(glob.glob(pat)))
    for p in files:
        tag = os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p)
        n = 0
        with open(p, encoding="utf-8") as f:
            for ln in f:
                if not ln.strip():
                    continue
                try:
                    r = json.loads(ln)
                except Exception:
                    unparsable[tag] += 1
                    continue
                n += 1
                nm = r.get("name")
                if not nm:
                    unparsable[tag] += 1
                    continue
                cur = best.get(nm)
                if cur is None:
                    best[nm] = r
                else:
                    dup[nm] += 1
                    if rank(r) > rank(cur):
                        best[nm] = r
        per_file[tag] = n

    print("ROW FILES (%d files, %d records):" % (len(files), sum(per_file.values())))
    for tag, n in per_file.items():
        print("  %-42s %6d" % (tag, n))
    if unparsable:
        print("UNPARSABLE LINES:", dict(unparsable))
    print()
    print("unique shader names with a row : %d" % len(best))
    print("records collapsed as duplicates : %d (across %d names)"
          % (sum(dup.values()), len(dup)))

    per = defaultdict(Counter)
    stage_of = {}
    for nm, r in best.items():
        st = r.get("stage") or "?"
        stage_of[nm] = st
        c = per[st]
        c["rows"] += 1
        for k in ("spirv_ok", "as_ok", "val_ok", "val13_ok"):
            if r.get(k):
                c[k] += 1
        if r.get("error"):
            c["with_error"] += 1
        if r.get("wave64"):
            c["wave64"] += 1

    cols = ("rows", "spirv_ok", "as_ok", "val_ok", "val13_ok", "wave64", "with_error")
    print()
    print("%-5s %s" % ("stage", " ".join("%9s" % c for c in cols)))
    tot = Counter()
    for st in STAGES + ("?",):
        if st not in per:
            continue
        c = per[st]
        print("%-5s %s" % (st, " ".join("%9d" % c[k] for k in cols)))
        tot.update(c)
    print("%-5s %s" % ("ALL", " ".join("%9d" % tot[k] for k in cols)))

    print()
    print("vs/ps/ms/gs only (the 'non-compute corpus' headline):")
    for k in ("rows", "spirv_ok", "as_ok", "val_ok", "val13_ok"):
        v = sum(per[s][k] for s in ("vs", "ps", "ms", "gs"))
        print("  %-9s %6d" % (k, v))

    print()
    print("TOP ERROR MESSAGES (normalised to first 90 chars):")
    ec = Counter()
    for r in best.values():
        e = r.get("error")
        if e:
            ec[e[:90]] += 1
    for e, n in ec.most_common(25):
        print("  %5d  %s" % (n, e))

    if out:
        json.dump({"n_rows": len(best),
                   "per_stage": {s: dict(per[s]) for s in per},
                   "duplicates": sum(dup.values()),
                   "rows": best}, open(out, "w", encoding="utf-8"), indent=0)
        print("\nwrote", out)


if __name__ == "__main__":
    main()
