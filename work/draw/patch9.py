p = 'work/draw/pdecode.py'
s = open(p, encoding='utf-8').read()
s = s.replace("            refSize = 2 if (cf & 0x80000000) else 4",
              "            refSize = 2 if (cf & 0x80000000) else 4\n"
              "            print('    layout: clusters', clusterCount, 'tris', tris, 'refs', refs, 'ilen', ilen,"
              " 'bones', bones, 'hint', (cf >> 16) & 0x1FFF, 'const', (cf & 0x20000000) != 0,"
              " 'tail', ilen - (12 + clusterCount * 16 + tris * 4 + refs * refSize))")
open(p, 'w', encoding='utf-8').write(s)
print('patched pdecode')
