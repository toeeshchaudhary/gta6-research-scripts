import sys
import numpy as np
import zlib, struct


def read_png(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, idat, w, h, bitd, ctype = 8, b'', 0, 0, 0, 0
    while pos < len(data):
        n = struct.unpack('>I', data[pos:pos+4])[0]
        typ = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+n]
        if typ == b'IHDR':
            w, h, bitd, ctype = struct.unpack('>IIBB', chunk[:10])
        elif typ == b'IDAT':
            idat += chunk
        elif typ == b'IEND':
            break
        pos += 12 + n
    raw = zlib.decompress(idat)
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    assert bitd == 8
    stride = w * ch
    out = np.zeros((h, stride), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.uint8)
    at = 0
    for y in range(h):
        f = raw[at]; at += 1
        line = np.frombuffer(raw[at:at+stride], dtype=np.uint8).copy(); at += stride
        if f == 1:
            for i in range(ch, stride):
                line[i] = (int(line[i]) + int(line[i - ch])) & 0xFF
        elif f == 2:
            line = (line.astype(np.int16) + prev.astype(np.int16)).astype(np.uint8)
        elif f == 3:
            for i in range(stride):
                a = int(line[i - ch]) if i >= ch else 0
                line[i] = (int(line[i]) + ((a + int(prev[i])) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = int(line[i - ch]) if i >= ch else 0
                b = int(prev[i])
                c = int(prev[i - ch]) if i >= ch else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (int(line[i]) + pr) & 0xFF
        out[y] = line
        prev = line
    return out.reshape(h, w, ch)[:, :, :3].astype(np.int16)


for path in sys.argv[1:]:
    img = read_png(path)
    h, w, _ = img.shape
    bg = img[0, 0]
    d = np.abs(img - bg).sum(axis=2)
    mask = d > 24
    cov = 100.0 * mask.sum() / mask.size
    ys, xs = np.nonzero(mask)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if mask.any() else None
    col = img.reshape(-1, 3)
    packed = (col[:, 0].astype(np.int32) << 16) | (col[:, 1].astype(np.int32) << 8) | col[:, 2]
    distinct = int(np.unique(packed).size)
    print(f'{path}: {w}x{h} bg={tuple(int(v) for v in bg)} covered={cov:.2f}% bbox={bbox} '
          f'colors={distinct} std={img.std():.1f}')
