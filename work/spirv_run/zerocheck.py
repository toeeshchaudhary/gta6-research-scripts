"""Find zero-filled (truncated by the session crash) artifacts."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIRS = ["s2_in/disasm", "cs_in/disasm", "spirv_s2", "spirv", "spirv_s2_unp"]


def zero(p):
    try:
        with open(p, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    return True
                if b.strip(b"\x00"):
                    return False
    except OSError:
        return None


for d in DIRS:
    p = os.path.join(HERE, d)
    if not os.path.isdir(p):
        continue
    tot = z = 0
    names = []
    for f in os.listdir(p):
        fp = os.path.join(p, f)
        if not os.path.isfile(fp):
            continue
        tot += 1
        if zero(fp):
            z += 1
            if len(names) < 5:
                names.append(f)
    print("%-18s files %6d  zero-filled %6d  %s" % (d, tot, z, names))
    if d.endswith("disasm"):
        with open(os.path.join(HERE, "zero_" + os.path.basename(d) + "_" + d.split("/")[0] + ".txt"), "w",
                  encoding="utf-8") as fh:
            for f in os.listdir(p):
                if f.endswith(".s") and zero(os.path.join(p, f)):
                    fh.write(f[:-2] + "\n")
