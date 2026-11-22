"""Classify the ASR transcripts of the 150-clip probe into speech / non-speech and summarise."""
import csv
import json
import os
import re
import statistics

here = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(here, "asr_results.csv"), encoding="utf-8-sig")))
sel = {r["file"]: r for r in json.load(open(os.path.join(here, "asr_clips", "selection.json"), encoding="utf-8"))}

speech, sfx, empty = [], [], []
for r in rows:
    t = (r["transcript"] or "").strip()
    words = [w for w in re.findall(r"[A-Za-z']+", t)]
    only_sfx = bool(re.match(r"^[\(\*\[](.*)[\)\*\]\s.]*$", t)) and len(words) < 4
    if not t:
        empty.append(r)
    elif len(words) >= 2 and not only_sfx:
        speech.append((r, t, len(words)))
    else:
        sfx.append((r, t))

n = len(rows)
print(f"clips {n}  speech {len(speech)}  sfx {len(sfx)}  empty {len(empty)}")
nonempty = n - len(empty)
print(f"speech share of non-empty clips: {100*len(speech)/nonempty:.1f}%   of all clips: {100*len(speech)/n:.1f}%")


def med(xs):
    return round(statistics.median(xs), 3) if xs else None


sp_d = [sel[r["file"]]["dur"] for r, _, _ in speech if r["file"] in sel]
sf_d = [sel[r["file"]]["dur"] for r, _ in sfx if r["file"] in sel]
sp_b = [sel[r["file"]]["bps"] for r, _, _ in speech if r["file"] in sel]
sf_b = [sel[r["file"]]["bps"] for r, _ in sfx if r["file"] in sel]
print(f"duration median  speech {med(sp_d)} s  non-speech {med(sf_d)} s")
print(f"bitrate  median  speech {med(sp_b)} bps  non-speech {med(sf_b)} bps")

# crude discriminators, evaluated on this labelled set
def score(rule, items):
    ok = sum(1 for r in items if rule(sel[r["file"]]))
    return round(100 * ok / max(1, len(items)), 1)


def rule_bps(s):
    return s["bps"] <= 40000


def rule_dur(s):
    return s["dur"] >= 1.0


print(f"rule bps<=40k: keeps {score(rule_bps, [r for r, _, _ in speech])}% of speech, "
      f"{score(rule_bps, [r for r, _ in sfx])}% of non-speech")
print(f"rule dur>=1s : keeps {score(rule_dur, [r for r, _, _ in speech])}% of speech, "
      f"{score(rule_dur, [r for r, _ in sfx])}% of non-speech")

out = {
    "clips": n, "speechClips": len(speech), "nonSpeechClips": len(sfx), "emptyTranscripts": len(empty),
    "speechShareNonEmptyPct": round(100 * len(speech) / nonempty, 1),
    "speechMedianDur": med(sp_d), "nonSpeechMedianDur": med(sf_d),
    "speechMedianBps": med(sp_b), "nonSpeechMedianBps": med(sf_b),
    "speechFiles": [],
}
best = sorted(speech, key=lambda x: -len(x[1]))[:24]
for r, t, _ in speech:
    s = sel[r["file"]]
    item = dict(file=r["file"], transcript=t, dur=s["dur"], bps=s["bps"], bank=s["bank"],
                bankOffset=s["bankOffset"], stream=s["stream"])
    out["speechFiles"].append(item)
out["curated"] = [dict(file=r["file"], transcript=t, dur=sel[r["file"]]["dur"], bps=sel[r["file"]]["bps"],
                       bank=sel[r["file"]]["bank"], bankOffset=sel[r["file"]]["bankOffset"],
                       stream=sel[r["file"]]["stream"]) for r, t, _ in best]
json.dump(out, open(os.path.join(here, "asr_summary.json"), "w", encoding="utf-8"), indent=1)
print(f"\n{len(best)} curated lines for the sample set")
for r, t, _ in best:
    s = sel[r["file"]]
    print(f"  {s['dur']:5.2f}s {s['bps']:6d}bps  {t[:100]}")
