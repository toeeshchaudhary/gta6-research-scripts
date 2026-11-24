"""Task 2b: reassemble the zlib page-runs of script.rpf's non-PSIN entries into whole images
and characterise them. Also reports the exact page grid.
"""
import os, sys, re, collections, struct

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(B, "work", "story")
D = os.path.join(B, "work", "lineage", "bin", "Release", "net8.0", "out_script")

def main():
    files = []
    for fn in os.listdir(D):
        m = re.match(r"big_([0-9a-f]{8})_(\d+)\.bin$", fn)
        if m:
            files.append((int(m.group(1), 16), int(m.group(2)), os.path.join(D, fn)))
    files.sort()
    print("big_ (unclassified-page) inflates:", len(files))
    for off, ln, p in files[:50]:
        print(f"  0x{off:08x} {ln:7d}")
    # the @0x53000 entry: pages from 0x53000 to 0xC3C00
    pages = []
    for fn in os.listdir(D):
        m = re.match(r"([0-9a-f]{8})_(\d+)\.bin$", fn)
        if not m: continue
        off = int(m.group(1), 16)
        if 0x53000 <= off < 0xC3C00:
            pages.append((off, int(m.group(2)), os.path.join(D, fn)))
    pages.sort()
    print(f"\npages in [0x53000,0xC3C00): {len(pages)}")
    blob = b""
    for off, ln, p in pages:
        b = open(p, "rb").read()
        print(f"  0x{off:08x} {len(b):6d} -> image[{len(blob):#x}]  {b[:8].hex()}")
        blob += b
    open(os.path.join(OUT, "script_rpf_image.bin"), "wb").write(blob)
    print(f"reassembled image = {len(blob):,} bytes ({len(blob):#x})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
