"""Final accounting numbers for the report: hole exposure of bank data and the totals."""
import json
import os

here = os.path.dirname(os.path.abspath(__file__))
idx = json.load(open(os.path.join(here, "audio_index.json"), encoding="utf-8"))
banks = idx["banks"]

fully = sum(1 for b in banks if b["holeBytes"] is not None and b["holeBytes"] >= b["size"])
partial = sum(1 for b in banks if b["holeBytes"])
print(f"banks {len(banks):,}  with any hole {partial:,}  fully inside holes {fully:,}")
print(f"declared bank bytes {sum(b['size'] for b in banks):,}  in holes {sum(b['holeBytes'] or 0 for b in banks):,}")

streams = [s for b in banks for s in b["streams"]]
print(f"streams {len(streams):,}  seconds {sum(s['dur'] for s in streams):,.1f} "
      f"({sum(s['dur'] for s in streams)/3600:,.2f} h)")
by = {}
for s in streams:
    d = by.setdefault(s["codec"], {"n": 0, "secs": 0.0, "bytes": 0})
    d["n"] += 1
    d["secs"] += s["dur"]
    d["bytes"] += s["bytes"]
for k, v in sorted(by.items()):
    print(f"  codec {k:>2}: {v['n']:>9,} streams, {v['secs']/3600:9.2f} h, {v['bytes']/2**20:9.1f} MiB of packet data")
