"""Task 3 (v2): hunt for a 32-entry tag table by *density*, which is layout-agnostic.

Pass A (density): count tag occurrences per 4 KiB window; expected by chance = 2, so >=12 is a
signal. Report those windows.
Pass B (table shapes): inside/over the whole file also test
   - 32 u16 in 64 B  with >= 8 matches and >= 6 distinct
   - 32 u32 in 128 B with >= 8 matches and >= 6 distinct
Hits append to tagscan_hits.txt.

Usage: s10_tagscan2.py <file> [...]
"""
import os, sys, struct, time
import numpy as np

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
TAGS = np.array(sorted(int(x, 16) for x in open(os.path.join(OUT, "tags32.txt")).read().split()), dtype=np.uint16)
TSET = {int(x) for x in TAGS}
LUT = np.zeros(65536, dtype=np.uint8)
LUT[TAGS] = 1
CHUNK = 64 << 20
PAD = 8192

def win_counts(mask, w):
    c = np.concatenate(([0], np.cumsum(mask, dtype=np.int32)))
    cnt = c[w:] - c[:len(c) - w]
    return cnt

def scan(path, base, prev, blk):
    buf = prev + blk
    a = np.frombuffer(buf, dtype=np.uint8)
    a16 = a[:len(a) // 2 * 2].view(np.uint16)
    mask = LUT[a16]
    # A: 4 KiB windows (2048 u16)
    cnt = win_counts(mask, 2048)
    for i in np.nonzero(cnt >= 12)[0]:
        off = base - len(prev) + i * 2
        sec = buf[i * 2:i * 2 + 4096]
        hit("A", path, off, int(cnt[i]),
            "distinct=%d" % len({int(x) for x in np.frombuffer(sec, dtype=np.uint16)} & TSET),
            sec[:96].hex())
    # B1: 32 u16 in 64 B
    idx = np.nonzero(mask.astype(np.int32)[:len(mask) - 32] * 0 + 1)[0]  # dummy
    c2 = win_counts(mask, 32)
    for i in np.nonzero(c2 >= 8)[0]:
        w = np.frombuffer(buf, dtype=np.uint16, count=32, offset=i * 2)
        d = len({int(x) for x in w} & TSET)
        if d < 6: continue
        hit("B1", path, base - len(prev) + i * 2, int(c2[i]), "distinct=%d" % d,
            buf[i * 2:i * 2 + 64].hex())
    # B2: 32 u32 in 128 B
    a32 = a[:len(a) // 4 * 4].view(np.uint32)
    m32 = LUT[a32 & 0xFFFF]
    c3 = win_counts(m32, 32)
    for i in np.nonzero(c3 >= 8)[0]:
        w = np.frombuffer(buf, dtype=np.uint32, count=32, offset=i * 4)
        d = len({int(x) & 0xFFFF for x in w} & TSET)
        if d < 6: continue
        hit("B2", path, base - len(prev) + i * 4, int(c3[i]), "distinct=%d" % d,
            buf[i * 4:i * 4 + 128].hex())

fh_out = open(os.path.join(OUT, "tagscan_hits.txt"), "a", encoding="utf-8")
fh_log = open(os.path.join(OUT, "tagscan.log"), "a", encoding="utf-8")

def hit(kind, path, off, cnt, extra, hexs):
    rec = f"{kind}\t{os.path.basename(path)}\t{off:#x}\tcount={cnt}\t{extra}\t{hexs}"
    fh_out.write(rec + "\n"); fh_out.flush()
    log("  HIT " + rec[:200])

def log(m):
    line = f"{time.strftime('%H:%M:%S')} {m}"
    print(line, flush=True); fh_log.write(line + "\n"); fh_log.flush()

def main():
    log(f"=== tagscan2 start ({len(TAGS)} tags)")
    for path in sys.argv[1:]:
        if not os.path.isfile(path):
            log("missing " + path); continue
        size = os.path.getsize(path); t0 = time.time(); done = 0
        log(f"scan {path} ({size:,} B)")
        with open(path, "rb", buffering=0) as f:
            prev = b""; base = 0
            while True:
                blk = f.read(CHUNK)
                if not blk: break
                scan(path, base + len(blk), prev, blk)
                done += len(blk); base += len(blk); prev = (prev + blk)[-PAD:]
                if base % (1 << 30) < CHUNK:
                    el = max(time.time() - t0, 1e-9)
                    log(f"  {done/2**30:.1f} GiB at {done/2**20/el:.0f} MiB/s")
        log(f"done {path} in {time.time()-t0:.0f}s")
    log("=== tagscan2 end")
    return 0

if __name__ == "__main__":
    sys.exit(main())
