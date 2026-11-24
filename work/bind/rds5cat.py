import struct, sys, json, os

def align(v, b):
    return (v + b - 1) // b * b

def cat(path):
    """Read RDS5 header + ETPF catalogue without decompressing any texture data."""
    with open(path, 'rb') as f:
        data = f.read(4096 * 4)
        fsize = os.path.getsize(path)
        magic = data[:4]
        if magic != b'RDS5':
            return {'path': path, 'ok': False, 'err': 'bad magic %r' % magic, 'size': fsize}
        count = struct.unpack_from('<I', data, 4)[0]
        sizeword = struct.unpack_from('<Q', data, 8)[0]
        v32_16 = struct.unpack_from('<I', data, 16)[0]
        alignword = struct.unpack_from('<I', data, 20)[0]
        virtual_size = sizeword & 0x00FFFFFFFFFFFFFF
        meta = {
            'path': path, 'size': fsize, 'count': count,
            'virtual_size': virtual_size, 'size_word_hi': sizeword >> 56,
            'w16': v32_16, 'w16_expect': (count + 31) // 32,
            'alignword': alignword,
        }
        table_end = 24 + (count - 1) * 8
        etpf = align(table_end, 256)
        meta['etpf_off'] = etpf
        f.seek(0); table = f.read(table_end)
        recs = []
        def soff(v): return (v & 0x3FFFFFF) * 256
        def voff(v): return ((v >> 30) & 0x3FFFFF) * 4096
        nchunks = count - 2
        prev_end = None
        okchunks = True
        for i in range(nchunks):
            v = struct.unpack_from('<Q', table, 24 + i * 8)[0]
            s = soff(v); vt = voff(v)
            if prev_end is not None and s < prev_end:
                okchunks = False
            prev_end = s
            recs.append((s, vt, (v >> 52), (v >> 26) & 15))
        meta['chunks_ordered'] = okchunks
        meta['chunk_count'] = nchunks
        meta['chunk0'] = recs[0] if recs else None
        # sentinel
        sv = struct.unpack_from('<Q', table, table_end - 8)[0]
        meta['sentinel_ok'] = (soff(sv) == fsize and voff(sv) == virtual_size)
        f.seek(etpf); eh = f.read(16)
        if eh[:4] != b'ETPF':
            meta['ok'] = False; meta['err'] = 'no ETPF at %d: %r' % (etpf, eh[:8])
            return meta
        ver, ntex, area = struct.unpack_from('<III', eh, 4)
        meta.update(ok=True, etpf_version=ver, textures=ntex, area=area)
        f.seek(etpf + 16); records = f.read(area)
        f.seek(etpf + 16 + area); ids = f.read(ntex * 32)
        meta['ids_read'] = len(ids) // 32
        tex = []
        for i in range(ntex):
            p = i * 16
            if p + 16 > len(records):
                break
            a, b, c, d = struct.unpack_from('<IIII', records, p)
            nonTail = b & 7; packedMips = a >> 28; mode = (b >> 23) & 0x1ff
            w = (a & 0x3FFF) + 1; h = ((a >> 14) & 0x3FFF) + 1
            fmt = (b >> 3) & 255; depth = ((b >> 11) & 1023) + 1; dim = (b >> 21) & 3
            base = (c & 0x1FFFFF) * 4096
            tid = ids[i*32:(i+1)*32].hex() if (i+1)*32 <= len(ids) else ''
            o = p + 8
            # 64-bit asset key lives right after the fixed descriptors
            kat = ntex * 16 + i * 8
            key = None
            if kat + 8 <= len(records):
                key = struct.unpack_from('<Q', records, kat)[0]
            tex.append({'i': i, 'w': w, 'h': h, 'fmt': fmt, 'mips': packedMips + nonTail,
                        'nonTail': nonTail, 'packed': packedMips, 'mode': mode, 'depth': depth,
                        'dim': dim, 'base': base, 'id': tid, 'key': key, 'd': d, 'c_hi': c >> 21})
        meta['tex'] = tex
        return meta

if __name__ == '__main__':
    m = cat(sys.argv[1])
    if '-s' in sys.argv:
        m.pop('tex', None)
    else:
        t = m.get('tex', [])
        if len(t) > int(os.environ.get('MAXTEX', '12')):
            m['tex'] = t[:int(os.environ.get('MAXTEX', '12'))]
            m['tex_truncated'] = True
    print(json.dumps(m, indent=1))
