"""Harvest identifier-shaped tokens from the preserved documents (work/meta/docs) and from
extracted asset filenames, then emit candidate tokens for dictionary/pattern use.

Usage: python -I harvest_docs.py <docsdir> <assetsdir> <out.txt>
"""
import os
import re
import sys

# identifiers, dotted names, paths, numbers-bearing names
TOK = re.compile(rb"[A-Za-z_][A-Za-z0-9_.:/\\\-]{2,200}")


def main():
    docs, assets, out = sys.argv[1], sys.argv[2], sys.argv[3]
    toks = set()
    n = 0
    for root, _, files in os.walk(docs):
        for fn in files:
            n += 1
            p = os.path.join(root, fn)
            try:
                with open(p, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            for m in TOK.finditer(data):
                s = m.group(0).decode("latin-1")
                toks.add(s)
                for part in re.split(r"[./:\\]", s):
                    if len(part) >= 3:
                        toks.add(part)
            base = os.path.splitext(fn)[0]
            for part in base.split("_"):
                toks.add(part)
    print(f"docs files read: {n}, tokens {len(toks)}", flush=True)
    for root, _, files in os.walk(assets):
        for fn in files:
            stem = os.path.splitext(fn)[0]
            toks.add(stem)
            # strip the generated "<n>_<kind>_<n>_" prefix of recovered names
            for part in stem.split("_"):
                if len(part) >= 3:
                    toks.add(part)
    print(f"after asset names: {len(toks)}", flush=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for s in sorted(toks):
            f.write(s + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
