"""ASCII/stat preview of a PNG written by the engine (no PIL available here).

usage: python -I work\\missionrt\\png_prev.py <file.png> [width]
"""
import struct
import sys
import zlib

BG = (15, 17, 23)


def load(path):
    b = open(path, "rb").read()
    assert b[:8] == b"\x89PNG\r\n\x1a\n", "not a png"
    i = 8
    w = h = bd = ct = 0
    idat = b""
    while i < len(b):
        ln = struct.unpack_from(">I", b, i)[0]
        typ = b[i + 4:i + 8]
        data = b[i + 8:i + 8 + ln]
        if typ == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", data[:10])
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
        i += 12 + ln
    raw = zlib.decompress(idat)
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    stride = w * ch
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if f == 1:
            for x in range(ch, stride):
                line[x] = (line[x] + line[x - ch]) & 0xFF
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif f == 3:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 0xFF
        elif f == 4:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                c = prev[x - ch] if x >= ch else 0
                bb = prev[x]
                pa, pb, pc = abs(bb - c), abs(a - c), abs(a + bb - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (bb if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, ch, out


def main():
    path = sys.argv[1]
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    w, h, ch, px = load(path)
    rows = max(1, cols * h // w // 2)
    chars = " .:-=+*#%@"
    lit = 0
    tot = 0
    for y in range(rows):
        line = ""
        for x in range(cols):
            sx = min(w - 1, x * w // cols)
            sy = min(h - 1, y * h // rows)
            o = (sy * w + sx) * ch
            r, g, b = px[o], px[o + 1], px[o + 2]
            tot += 1
            isbg = max(abs(r - BG[0]), abs(g - BG[1]), abs(b - BG[2])) < 18
            if isbg:
                line += " "
            else:
                lit += 1
                v = (r * 299 + g * 587 + b * 114) // 1000 / 255.0
                line += chars[min(9, int(v * 10))]
        print(line)
    print("non-background %.1f%% of %dx%d" % (100.0 * lit / tot, w, h))


if __name__ == "__main__":
    main()
