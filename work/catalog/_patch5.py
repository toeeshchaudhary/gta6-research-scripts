p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('''A("* **Phase labels.** Keyword matching with arbitrary precedence on 23 % non-matching names.")''',
'''A("* **Phase labels.** Keyword matching with arbitrary precedence: %d of %d named states (%.0f %%) match"
  % (A_["named_states"] - sum(COV["primary_states_after"].values()), A_["named_states"],
     100.0 * (A_["named_states"] - sum(COV["primary_states_after"].values())) / A_["named_states"]))
A("  no keyword at all (`Fence`, `Chamber`, `Storage`, place and role names).")''')
s=s.replace('''A("**What would move the needle, in order:** (1) finish the pair sweep for the five open state hashes")
A("(`BRUTE.md` §6); (2) reconcile the `introCS`/`introcS` capitalisation variants; (3) treat state clusters")
A("as the unit of naming — one decoded member names a whole cluster, and clusters cover 82 % of files.")''',
'''A("**What would move the needle, in order:** (1) find a mission→file binding for the other 2,034 outlines")
A("— everything else in this catalogue is downstream of that one gap; (2) resolve the four position-only")
A("hashes (`BRUTE.md` §7) with a 3-token sweep restricted to state-word slots; (3) treat state clusters as")
A("the unit of naming — one decoded member names a whole cluster, and clusters cover 82 % of files.")''')
open(p,"w",encoding="utf-8").write(s)
print("ok")
