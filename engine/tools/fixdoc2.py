p="ENGINE.md"
s=open(p,encoding="utf-8").read()
s=s.replace("| 1 handguard | 17,168 | **0.224 ms** | 4,466 |","| 1 handguard | 17,168 | **0.17?0.22 ms** (0.165, 0.202, 0.224 over three runs) | 4,500?6,100 |")
s=s.replace("| 1 handguard @ 1920x1061 | 17,168 | 0.216 ms | 4,640 |","| 1 handguard @ 1920x1061 | 17,168 | 0.216 ms | 4,640 |")
open(p,"w",encoding="utf-8").write(s)
