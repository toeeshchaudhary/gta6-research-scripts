p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('A("checked against `work/arch/out/bindings.json` — and, as §6.1 shows, none of them resolve.")',
            'A("checked against `work/arch/out/bindings.json` — and, as the paragraph below shows, none resolve.")')
open(p,"w",encoding="utf-8").write(s)
