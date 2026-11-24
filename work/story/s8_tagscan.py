"""Task 3: hunt for the decoder's 32-entry tag table in the huge archives.

Looks for a 64-byte window (32 consecutive u16) holding >=12 of the 32 unknown-codec tags with >=8
distinct values, in any order. Also (b) a 128-byte window of 32 u32 holding >=12 tags (widened table).

Usage: s8_tagscan.py <file> [<file> ...]
Results append to tagscan_hits.txt, one line per hit, plus progress in tagscan.log.
"""
import os, sys, struct, time
import numpy as np

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
TAGS = np.array(sorted(int(x, 16) for x in open(os.path.join(OUT, "tags32.txt")).read().split()), dtype=np.uint16)
CHUNK = 64 << 20
PAD = 256

def windows(mask, w):
    """indices i where sum(mask[i:i+w]) high"""
    c = np.concatenate(([0], np.cumsum(mask, dtype=np.int32)))
    if len(mask) <= w: return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int32)
    cnt = c[w:] - c[:len(c) - w]
    idx = np.nonzero(cnt >= 12)[0]
    return idx, cnt[idx]

def scan_u16(b, base, fh, log):
    a = np.frombuffer(b, dtype=np.uint8)
    if len(a) < 128: return
    a16 = a[:len(a) // 2 * 2].view(np.uint16)
    mask = np.isin(a16, TAGS)
    idx, cnt = windows(mask, 32)
    for i in idx:
        win = a16[i:i + 32]
        wb = win.tobytes()
        vals = set(struct.unpack_from("<%dH" % len(win), wb, 0))
        distinct = len(vals & {int(x) for x in TAGS})
        if distinct < 8: continue
        off = base + i * 2
        rec = f"U16\t{fh}\t{off:#x}\tcount={int(cnt[i])}\tdistinct={distinct}\t{b[i*2:i*2+64].hex()}"
        fh_out.write(rec + "\n"); fh_out.flush()
        log(f"  HIT {rec[:160]}")

def scan_u32(b, base):
    a = np.frombuffer(b, dtype=np.uint8)
    a32 = a[:len(a) // 4 * 4].view(np.uint32)
    tl = {int(x) for x in TAGS}
    mask = np.isin(a32 & 0xFFFF, TAGS)
    idx, cnt = windows(mask, 32)
    for i in idx:
        vals = [int(v) & 0xFFFF for v in a32[i:i + 32]]
        distinct = len(set(vals) & tl)
        if distinct < 8: continue
        off = base + i * 4
        rec = f"U32\t{fh}\t{off:#x}\tcount={int(cnt[i])}\tdistinct={distinct}\t{b[i*4:i*4+128].hex()}"
        fh_out.write(rec + "\n"); fh_out.flush()
        log(f"  HIT {rec[:160]}")

fh_out = open(os.path.join(OUT, "tagscan_hits.txt"), "a", encoding="utf-8")
fh_log = open(os.path.join(OUT, "tagscan.log"), "a", encoding="utf-8")

def log(m):
    line = f"{time.strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    fh_log.write(line + "\n"); fh_log.flush()

def main():
    log(f"=== tagscan start, tags={len(TAGS)}")
    for path in sys.argv[1:]:
        if not os.path.isfile(path):
            log(f"missing {path}"); continue
        size = os.path.getsize(path)
        t0 = time.time(); done = 0
        log(f"scan {path} ({size:,} B)")
        with open(path, "rb", buffering=0) as f:
            prev = b""
            base = 0
            while True:
                blk = f.read(CHUNK)
                if not blk: break
                buf = prev + blk
                scan_u16(buf, base, path, log)
                scan_u32(buf, base)
                done += len(blk); base += len(blk)
                prev = buf[-PAD:]
                if done % (1 << 30) < CHUNK:
                    el = time.time() - t0
                    log(f"  {done/2**30:.1f} GiB at {done/2**20/max(el,1e-9):.0f} MiB/s")
        log(f"done {path} in {time.time()-t0:.0f}s")
    log("=== tagscan end")
    return 0

if __name__ == "__main__":
    sys.exit(main())
