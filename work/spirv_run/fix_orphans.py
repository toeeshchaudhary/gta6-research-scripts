"""Repair orphan rows: re-assemble .spv files that were zero-filled by a crashed shard, and retry
one transient spirv-val failure. Rewrites the row file in place.

usage: python fix_orphans.py <spirv dir> <rows jsonl>
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIRV = os.path.join(HERE, "..", "spirv")


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stderr or "").strip()


def val(spv, env):
    for attempt in range(2):
        rc, err = run([os.path.join(SPIRV, "spirv-val.exe"), "--target-env", env,
                       "--allow-offset-texture-operand", spv])
        if rc == 0:
            return True, ""
    return False, err


def main():
    spirv, rowsf = sys.argv[1], sys.argv[2]
    rows = [json.loads(l) for l in open(rowsf, encoding="utf-8") if l.strip()]
    fixed_as = fixed_retry = 0
    for r in rows:
        if r["val_ok"] and r["val13_ok"]:
            continue
        spv = os.path.join(spirv, r["name"] + ".spv")
        asm = os.path.join(spirv, r["name"] + ".spvasm")
        head = open(spv, "rb").read(4)
        if head != b"\x03\x02\x23\x07":
            rc, err = run([os.path.join(SPIRV, "spirv-as.exe"), asm, "-o", spv,
                           "--target-env", "vulkan1.2"])
            if rc != 0:
                r["error"] = "as: " + (err.splitlines() or ["?"])[0][:160]
                continue
            r["as_ok"] = True
            fixed_as += 1
        ok12, e12 = val(spv, "vulkan1.2")
        ok13, e13 = val(spv, "vulkan1.3")
        if ok12 and r["val_ok"]:
            fixed_retry += 1
        r["val_ok"], r["val13_ok"] = ok12, ok13
        r["error"] = None if ok13 else ("val1.3: " + (e13.splitlines() or ["?"])[0][:160])
    with open(rowsf, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"reassembled {fixed_as}, val_ok {sum(r['val_ok'] for r in rows)}/{len(rows)}, "
          f"val13_ok {sum(r['val13_ok'] for r in rows)}/{len(rows)}, retried-fixed {fixed_retry}")


if __name__ == "__main__":
    sys.exit(main())
