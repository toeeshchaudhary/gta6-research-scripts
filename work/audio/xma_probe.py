"""Spot-check XMA2 (codec 5) streams: write RIFF XMA2 WAVs and compare declared vs ffmpeg-decoded length.

Usage: python -I xma_probe.py <awc_root> <index.json> <out_dir> [count]
"""
import json
import os
import struct
import sys


def write_xma_wav(path, d, ch, rate, samples, at, ln):
    h = bytearray(80)
    h[0:4] = b"RIFF"
    struct.pack_into("<I", h, 4, 72 + ln)
    h[8:16] = b"WAVEfmt "
    struct.pack_into("<I", h, 16, 52)
    struct.pack_into("<H", h, 20, 0x166)
    struct.pack_into("<H", h, 22, ch)
    struct.pack_into("<I", h, 24, rate)
    struct.pack_into("<I", h, 28, max(1, int(round(ln / (samples / rate)))))
    struct.pack_into("<H", h, 32, ch * 2)
    struct.pack_into("<H", h, 34, 16)
    struct.pack_into("<H", h, 36, 34)
    struct.pack_into("<H", h, 38, (ch + 1) // 2)
    struct.pack_into("<I", h, 40, 4 if ch == 1 else 3)
    struct.pack_into("<I", h, 44, samples * ch * 2)
    struct.pack_into("<I", h, 48, 0x8000)
    h[69] = 4
    struct.pack_into("<H", h, 70, (ln + 0x7FFF) // 0x8000)
    h[72:76] = b"data"
    struct.pack_into("<I", h, 76, ln)
    with open(path, "wb") as f:
        f.write(h)
        f.write(d[at:at + ln])


def main():
    root, index_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    os.makedirs(out, exist_ok=True)
    index = json.load(open(index_path, encoding="utf-8"))
    pool = [(b, s) for b in index["banks"] for s in b["streams"] if s["codec"] == 5]
    step = max(1, len(pool) // n)
    sel = pool[::step][:n]
    rows = []
    for b, s in sel:
        d = open(os.path.join(root, b["file"]), "rb").read()
        name = f"xma_{b['offset']:X}_{s['id']}.wav"
        write_xma_wav(os.path.join(out, name), d, s["ch"], s["sr"], s["samples"], s["off"], s["bytes"])
        rows.append(dict(file=name, bank=b["file"], stream=s["id"], ch=s["ch"], rate=s["sr"],
                         declaredSamples=s["samples"], declaredDur=s["dur"], bytes=s["bytes"]))
    json.dump(rows, open(os.path.join(out, "probe.json"), "w", encoding="utf-8"), indent=1)
    print(f"{len(rows)} xma probes -> {out}")


if __name__ == "__main__":
    main()
