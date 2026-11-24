"""Build the full adapter tree that rdna2spirv.py expects for the whole carve.

Creates under <out>:
    fssm/        junction to <corpus>/fssm
    <stem>.dxbc  hard link to <corpus>/<stem>.cso   (the tool looks for .dxbc names)
    index.json   [{"file": "<stem>.dxbc", "stage": "<vs|ps|ms|gs|cs>"}, ...]

The reference tool reads a shader's DXBC container as <parent>/<name>.dxbc and the stage from
index.json keys file[:-5], so the .dxbc spelling matters.

usage: python build_layout.py <corpus> <out>
"""
import json
import os
import subprocess
import sys


def main():
    corpus, out = sys.argv[1], sys.argv[2]
    idx = json.load(open(os.path.join(corpus, "index.json"), encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    jd = os.path.join(out, "fssm")
    if not os.path.isdir(jd):
        subprocess.run(["cmd", "/c", "mklink", "/J", jd, os.path.join(corpus, "fssm")], check=True,
                       capture_output=True)
    rows, linked, errs = [], 0, []
    for e in idx:
        stem = os.path.splitext(e["file"])[0]
        src = os.path.join(corpus, e["file"])
        dst = os.path.join(out, stem + ".dxbc")
        if not os.path.exists(dst):
            try:
                os.link(src, dst)
                linked += 1
            except OSError as ex:
                errs.append(f"{stem}: {ex}")
        rows.append({"file": stem + ".dxbc", "stage": e["stage_from_dxil"],
                     "endpgm": e.get("fssm_endpgm_count")})
    json.dump(rows, open(os.path.join(out, "index.json"), "w", encoding="utf-8"), indent=0)
    n = {}
    for r in rows:
        n[r["stage"]] = n.get(r["stage"], 0) + 1
    print(f"{len(rows)} entries, {linked} hard links created, {len(errs)} errors: {n}")
    for x in errs[:5]:
        print("  ", x)


if __name__ == "__main__":
    sys.exit(main())
