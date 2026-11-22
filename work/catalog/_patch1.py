import io
p = r"work\catalog\p4_catalog.py"
s = open(p, encoding="utf-8").read()
subs = [
 ('A("| distinct state slots in the outlines | **%d** |" % os_["states_total"])',
  'A("| distinct state slots in the outlines | **%s** |" % n(os_["states_total"]))'),
 ('A("| of which real states (non-structural) | **%d** |" % os_["real_states"])',
  'A("| of which real states (non-structural) | **%s** |" % n(os_["real_states"]))'),
 ('A("| real states that resolve to a name | **%d** (%.2f %% of real states) |" %\n  (os_["named_real_states"], 100.0 * os_["named_real_states"] / os_["real_states"]))',
  'A("| real states that resolve to a name | **%s** (%.2f %% of real states) |" %\n  (n(os_["named_real_states"]), 100.0 * os_["named_real_states"] / os_["real_states"]))'),
 ('A("| records in named states | **%d** |" % SH["records_in_named_states"])',
  'A("| records in named states | **%s** |" % n(SH["records_in_named_states"]))'),
 ('A("| records in unnamed-but-real states | **%d** |" % SH["records_in_unnamed_states"])',
  'A("| records in unnamed-but-real states | **%s** |" % n(SH["records_in_unnamed_states"]))'),
 ('A("| entity elements decoded in total | **%d** |" % os_["entities_total"])',
  'A("| entity elements decoded in total | **%s** |" % n(os_["entities_total"]))'),
 ('A("| %s | %d |" % (k, os_["size_classes"][k]))',
  'A("| %s | %s |" % (k, n(os_["size_classes"][k])))'),
 ('def row2(lbl, n):\n    A("| %s | **%d** | %.1f %% |" % (lbl, n, 100.0 * n / 2035))',
  'def row2(lbl, k):\n    A("| %s | **%s** | %.1f %% |" % (lbl, n(k), 100.0 * k / 2035))'),
 ('def row(lbl, n, tot=145, tag=""):\n    A("| %s | **%d** | %.1f %% |" % (lbl + tag, n, 100.0 * n / tot))',
  'def row(lbl, k, tot=145, tag=""):\n    A("| %s | **%s** | %.1f %% |" % (lbl + tag, n(k), 100.0 * k / tot))'),
 ('def jl(p): return json.load(open(p, encoding="utf-8"))',
  'def jl(p): return json.load(open(p, encoding="utf-8"))\ndef n(x): return "{:,}".format(int(x))'),
]
for a, b in subs:
    if a not in s:
        print("MISS:", a[:60])
    s = s.replace(a, b)
open(p, "w", encoding="utf-8").write(s)
print("ok")
