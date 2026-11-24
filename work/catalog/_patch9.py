p=r"work\catalog\p3_emit.py"
s=open(p,encoding="utf-8").read()
s=s.replace('L.append("| description key | `%s` | **proven** — literal `<ID>` in CMissions doc |" % m["description_key"])',
            'L.append("| description key | `%s` | **proven** — the `PROG_*_DESC_REPLAY` string in the CMissions document |" % m["description_key"])')
s=s.replace('L.append("| grid texture | `%s` | **proven** — literal `<ID>` token |" % m["grid_texture"])',
            'L.append("| grid texture | `%s` | **proven** — the `GRID_SML_L_*` string in the CMissions document |" % m["grid_texture"])')
open(p,"w",encoding="utf-8").write(s)
print("ok")
