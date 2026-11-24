"""Cross-check artifact sets: corpus vs disassembly vs spvasm/spv vs rows.

Answers, per stage: how many corpus shaders exist, how many have .s, how many have .spvasm,
how many have .spv, how many have a result row, and how the sets differ.
"""
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
R = HERE


def names(d, ext):
    p = os.path.join(R, d)
    if not os.path.isdir(p):
        return set()
    return {f[: -len(ext)] for f in os.listdir(p) if f.endswith(ext)}


idx_path = os.path.join(R, "s2_in", "index.json")
idx = json.load(open(idx_path, encoding="utf-8"))
stage = {}
for e in idx:
    stage[os.path.splitext(os.path.basename(e["file"]))[0]] = e.get("stage", "?")

corpus = set(stage)
print("index.json entries: %d, unique names: %d" % (len(idx), len(corpus)))
print("stage counts in index:", dict(Counter(stage.values())))

s_s2 = names(os.path.join("s2_in", "disasm"), ".s")
s_cs = names(os.path.join("cs_in", "disasm"), ".s")
s_old = names(os.path.join("spirv_in", "disasm"), ".s")
as_s2 = names("spirv_s2", ".spvasm")
spv_s2 = names("spirv_s2", ".spv")
as_o = names("spirv", ".spvasm")
spv_o = names("spirv", ".spv")
miss = names("s2_miss", ".fssm")

print("\n--- raw sets ---")
for nm, st in (("s2_in/disasm .s", s_s2), ("cs_in/disasm .s", s_cs), ("spirv_in/disasm .s", s_old),
               ("spirv_s2 .spvasm", as_s2), ("spirv_s2 .spv", spv_s2),
               ("spirv .spvasm", as_o), ("spirv .spv", spv_o), ("s2_miss .fssm", miss)):
    print("  %-22s %6d   (in corpus: %d, foreign: %d)"
          % (nm, len(st), len(st & corpus), len(st - corpus)))

print("\n--- overlaps ---")
print("  spirv .spvasm subset of spirv_s2: %s" % (as_o <= as_s2))
print("  spirv_s2 .spvasm only: %d ; spirv .spvasm only: %d" % (len(as_s2 - as_o), len(as_o - as_s2)))
print("  s2_miss already disassembled in s2_in: %d" % len(miss & s_s2))
print("  s2_miss already disassembled in cs_in: %d" % len(miss & s_cs))
print("  s2_miss really missing .s: %d" % len(miss - s_s2 - s_cs))

# per-stage table
all_s = s_s2 | s_cs
all_as = as_s2 | as_o
per = defaultdict(Counter)
for n in corpus:
    st = stage[n]
    c = per[st]
    c["corpus"] += 1
    if n in all_s:
        c["s"] += 1
    if n in all_as:
        c["spvasm"] += 1
    if n in spv_s2 or n in spv_o:
        c["spv"] += 1
print("\n%-5s %8s %8s %8s %8s" % ("stage", "corpus", ".s", ".spvasm", ".spv"))
for st in ("vs", "ps", "ms", "gs", "cs", "?"):
    if st in per:
        c = per[st]
        print("%-5s %8d %8d %8d %8d" % (st, c["corpus"], c["s"], c["spvasm"], c["spv"]))
tot = Counter()
for c in per.values():
    tot.update(c)
print("%-5s %8d %8d %8d %8d" % ("ALL", tot["corpus"], tot["s"], tot["spvasm"], tot["spv"]))

# rows coverage
rows = {}
for d in ("logs_s2", "logs"):
    p = os.path.join(R, d)
    for f in sorted(os.listdir(p)):
        if f.startswith("rows.part") and f.endswith(".jsonl"):
            for ln in open(os.path.join(p, f), encoding="utf-8"):
                if ln.strip():
                    r = json.loads(ln)
                    k = r["name"]
                    if k not in rows or (r.get("val_ok") and not rows[k].get("val_ok")):
                        rows[k] = r
print("\nrow names: %d ; in corpus: %d ; foreign: %d"
      % (len(rows), len(set(rows) & corpus), len(set(rows) - corpus)))
print("corpus shaders with .s but NO row: %d" % len(all_s - set(rows)))
print("corpus shaders with .spvasm but NO row: %d" % len(all_as - set(rows)))
print("corpus shaders with a row but NO .s: %d" % len(set(rows) - all_s))
