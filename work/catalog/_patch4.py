p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('"It reads as a staged photo/hanging beat with an optional fall. **One decoded member names all seven.**"',
            '"*Inferred* read: a staged photo/hanging beat with an optional fall. **One decoded member names all seven.**"')
s=s.replace('"`LOADOUT_DEFAULT` (a proven vocabulary word), it has `victimSaved`, and it places real entities. "\n     "It reads as a rescue encounter."',
            '"`LOADOUT_DEFAULT` (a base-vocabulary word), it has `victimSaved`, and its structural blob carries "\n     "295–441 decodable entity elements. *Inferred* read: a rescue encounter. Only `g0988` of the ten has a "\n     "full runtime placement (§6); the others are element counts, not placed coordinates."')
open(p,"w",encoding="utf-8").write(s)
print("ok")
