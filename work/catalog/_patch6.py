p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('A("* **Phase labels.** Keyword matching with arbitrary precedence: %d of %d named states (%.0f %%) match"\n  % (A_["named_states"] - sum(COV["primary_states_after"].values()), A_["named_states"],',
            'A("* **Phase labels.** Keyword matching with arbitrary precedence: %s of %s named states (%.0f %%) match"\n  % (n(A_["named_states"] - sum(COV["primary_states_after"].values())), n(A_["named_states"]),')
open(p,"w",encoding="utf-8").write(s)
print("ok")
