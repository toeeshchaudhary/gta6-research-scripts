p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('''    A("| %s | %d | %.2f %% | %d | %.2f %% |" % (lbl, r["distinct_resolved"], r["distinct_rate_pct"],
                                                r["key_records_resolved"], r["key_record_rate_pct"]))''',
'''    A("| %s | %d | %.2f %% | %s | %.2f %% |" % (lbl, r["distinct_resolved"], r["distinct_rate_pct"],
                                                n(r["key_records_resolved"]), r["key_record_rate_pct"]))''')
open(p,"w",encoding="utf-8").write(s)
