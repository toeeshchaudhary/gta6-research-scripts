import json, collections
O = json.load(open(r"work\catalog\out\_outlines.json", encoding="utf-8"))
for f in ["g0082_032AB000", "g0083_032AE000", "g0491_03984000", "g1599_0444F000", "g1020_03DE7000"]:
    o = O[f]
    print(f, "|", o["txt"])
    print("   notes:", [ (st["name"], st["name_src"]) for st in o["states"] if st.get("name_src","").startswith(("C:","A:")) ])
gains = []
for f, o in O.items():
    nb = sum(1 for st in o["states"] if st["name"] and st["name_src"] == "ship" and st["phase_before"])
    na = sum(1 for st in o["states"] if st["name"])
    nn = sum(1 for st in o["states"] if st.get("name_src","").startswith(("C:","A:")))
    if nn:
        gains.append((nn, o["named_real_states"], o["real_states"], f, o["txt"]))
gains.sort(reverse=True)
print("\nfiles with most expanded names:")
for g in gains[:12]:
    print(g[0], g[1], "/", g[2], g[3], "|", g[4][:150])
