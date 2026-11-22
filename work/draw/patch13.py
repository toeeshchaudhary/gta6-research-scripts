p=r'work/draw/cover.py'
s=open(p,encoding='utf-8').read()
s=s.replace("""    print(f'{path}: {w}x{h} bg={tuple(int(v) for v in bg)} covered={cov:.2f}% bbox={bbox}')""",
"""    col = img.reshape(-1, 3)
    packed = (col[:, 0].astype(np.int32) << 16) | (col[:, 1].astype(np.int32) << 8) | col[:, 2]
    distinct = int(np.unique(packed).size)
    print(f'{path}: {w}x{h} bg={tuple(int(v) for v in bg)} covered={cov:.2f}% bbox={bbox} '
          f'colors={distinct} std={img.std():.1f}')""")
open(p,'w',encoding='utf-8').write(s)
