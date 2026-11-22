import sys
def joaat(s, seed=0xB779A091):
    h = seed
    for ch in s.encode('utf-8'):
        h = (h + ch) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h
cands = ["VS_AlphaTransmissionFullScreenTri","vs_VS_AlphaTransmissionFullScreenTri",
         "vs_VS_AlphaTransmissionFullScreenTri_Wrapped","VS_AlphaTransmissionFullScreenTri_Wrapped",
         "AlphaTransmissionFullScreenTri"]
for c in cands:
    for seed in (0xB779A091, 0x3FAC7125, 0):
        print(f"{c!r:50} seed=0x{seed:08X} -> 0x{joaat(c,seed):08X}")
