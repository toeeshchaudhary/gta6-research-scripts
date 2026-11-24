p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('''    A("| %s | %d | %d | %d | %d → %d |" % (ph, psb.get(ph, 0), psa.get(ph, 0),
                                            PH["primary_records"].get(ph, 0),
                                            fpb.get(ph, 0), fp.get(ph, 0)))''',
'''    A("| %s | %s | %s | %s | %s → %s |" % (ph, n(psb.get(ph, 0)), n(psa.get(ph, 0)),
                                             n(PH["primary_records"].get(ph, 0)),
                                             n(fpb.get(ph, 0)), n(fp.get(ph, 0))))''')
s=s.replace('are not states, and 91 % of distinct hashes are still hex. `measured`.',
            'are not states, and 92 % of distinct hashes (5,591 of 6,065) are still hex. `measured`.')
s=s.replace('A("| state slots given a phase tag | %d | %d | +%d |" %',
            'A("| state slots given a phase tag | %s | %s | +%d |" %')
s=s.replace('  (sum(COV["primary_states_before"].values()), sum(COV["primary_states_after"].values()),',
            '  (n(sum(COV["primary_states_before"].values())), n(sum(COV["primary_states_after"].values())),')
open(p,"w",encoding="utf-8").write(s)
print("ok")
