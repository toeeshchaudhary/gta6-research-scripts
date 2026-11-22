p=r"work\catalog\p4_catalog.py"
s=open(p,encoding="utf-8").read()
s=s.replace('V = S.get("vocab", {})\nB_, A_ = V.get("before", {}), V.get("after", {})\nA("### 1.3 Vocabulary',
            'A("### 1.3 Vocabulary')
s=s.replace('RANK = jl(os.path.join(W, "mission2", "out", "_ranking.json"))',
            'RANK = jl(os.path.join(W, "mission2", "out", "_ranking.json"))\n_V = S.get("vocab", {})\nB_, A_ = _V.get("before", {}), _V.get("after", {})')
open(p,"w",encoding="utf-8").write(s)
print("ok")
