p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('A("## 6. World placement (the 9 runtime-decoded missions)")',
            'A("## 6. World placement (the %d runtime-decoded missions)" % len(PL))')
s=s.replace('A("layout from `MISSIONRT.md` §2). Entity positions are real world coordinates; archetype hashes are")\nA("resolved against `work/arch/out/bindings.json` where possible.")',
            'A("layout from `MISSIONRT.md` §2). Entity positions are real world coordinates. Archetype hashes are")\nA("checked against `work/arch/out/bindings.json` — and, as §6.1 shows, none of them resolve.")')
open(p,"w",encoding="utf-8").write(s)
print("ok")
