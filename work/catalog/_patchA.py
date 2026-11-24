p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('A("| records in named states | **%s** |" % n(SH["records_in_named_states"]))',
            'A("| records in named states (after the §1.3 overlay) | **%s** |" % n(A_["records_named"]))')
s=s.replace('A("| records in unnamed-but-real states | **%s** |" % n(SH["records_in_unnamed_states"]))',
            'A("| records in unnamed-but-real states | **%s** |" % n(40804 - SH["records_in_structural_states"] - A_["records_named"]))')
s=s.replace('''for key, lbl in [("base", "base dictionaries"), ("base_plus_A", "+ tier A (20 curated)"),
                 ("base_plus_A_plus_B", "+ tier B (230 brute-force)")]:''',
'''for key, lbl in [("base", "base dictionaries"), ("base_plus_A", "+ tier A (20 curated)"),
                 ("base_plus_A_plus_B", "+ tier B (230 brute-force)")]:''')
open(p,"w",encoding="utf-8").write(s)
print("ok")
