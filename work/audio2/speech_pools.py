"""Count the speech-candidate pools under different rules, using the index (no decoding)."""
import json
import os

here = os.path.dirname(os.path.abspath(__file__))
idx = json.load(open(os.path.join(here, "audio_index.json"), encoding="utf-8"))

rules = {
    "all_nonstreamed_opus_mono": lambda s: s["ch"] == 1,
    "dur_0.5_20_mono": lambda s: s["ch"] == 1 and 0.5 <= s["dur"] <= 20,
    "precision_bps<=40k_dur>=1": lambda s: s["ch"] == 1 and s["bps"] <= 40000 and s["dur"] >= 1.0,
    "precision_incl_short": lambda s: s["ch"] == 1 and s["bps"] <= 40000 and s["dur"] >= 0.5,
    "long_lines_dur>=4": lambda s: s["ch"] == 1 and s["dur"] >= 4.0,
}
res = {}
for name, rule in rules.items():
    n = 0
    secs = 0.0
    banks = set()
    for b in idx["banks"]:
        for s in b["streams"]:
            if s["codec"] == 0x0B and not s["streamed"] and rule(s):
                n += 1
                secs += s["dur"]
                banks.add(b["file"])
    res[name] = {"streams": n, "hours": round(secs / 3600, 2), "banks": len(banks)}
    print(f"{name:28s} {n:>9,} streams {secs/3600:9.2f} h  {len(banks):>5} banks")

json.dump(res, open(os.path.join(here, "speech_pools.json"), "w", encoding="utf-8"), indent=1)
