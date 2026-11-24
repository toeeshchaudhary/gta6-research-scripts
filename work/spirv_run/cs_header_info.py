"""Per-shader compute launch info straight out of the FSSM header (no disassembly needed).

COMPUTE_PGM_RSRC2 is the u32 at blob+0x138: USER_SGPR [5:1], TGID_X/Y/Z_EN [9:7], TG_SIZE_EN [10],
TIDIG_COMP_CNT [12:11], LDS_SIZE [23:15]. Words 0x13C..0x144 are the thread-group size.

Writes one json per shader so the failure taxonomy can be crossed with the launch-time register layout.
usage: python cs_header_info.py [--out hdr_info.jsonl]
"""
import argparse
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
FSSM = os.path.join(HERE, "cs_fssm")


def info(path):
    b = open(path, "rb").read(0x148)
    rsrc2, lx, ly, lz = struct.unpack_from("<4I", b, 0x138)
    return {
        "rsrc2": rsrc2,
        "user_sgprs": (rsrc2 >> 1) & 31,
        "tgid_en": (rsrc2 >> 7) & 7,
        "tg_size_en": (rsrc2 >> 10) & 1,
        "tidig": (rsrc2 >> 11) & 3,
        "lds_size": ((rsrc2 >> 15) & 0x1FF) * 128,
        "size": [lx, ly, lz],
        "threads": lx * ly * lz,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "hdr_info.jsonl"))
    a = ap.parse_args()
    names = sorted(f for f in os.listdir(FSSM) if f.endswith(".fssm"))
    n = 0
    with open(a.out, "w", encoding="utf-8") as fh:
        for f in names:
            r = {"name": os.path.splitext(f)[0]}
            try:
                r.update(info(os.path.join(FSSM, f)))
            except Exception as e:  # noqa: BLE001
                r["error"] = "%s: %s" % (type(e).__name__, e)
            fh.write(json.dumps(r) + "\n")
            n += 1
    print("%d blobs -> %s" % (n, a.out))


if __name__ == "__main__":
    main()
