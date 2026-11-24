"""step14_content.py - content-of-interest candidates inside the stitched resources, with hexdumps.
"""
import json, os, sys, struct, collections, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stitchlib as S

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "resources")
man = json.load(open(os.path.join(RES, "manifest.json")))

print("=== 1. ascending u32 tables with constant stride != 1 (index/switch candidates) ===")
found = []
for m in man:
    b = open(os.path.join(RES, m["resource"]), "rb").read()
    n = len(b) // 4
    d = struct.unpack_from("<%dI" % n, b, 0)
    i = 0
    while i < n - 6:
        j = i
        while j + 1 < n and 0 < d[j + 1] - d[j] < 0x1000:
            j += 1
        if j - i >= 5:
            deltas = [d[i + k + 1] - d[i + k] for k in range(j - i)]
            if len(set(deltas)) == 1 and deltas[0] not in (1, 2, 4):
                found.append((m["resource"], i * 4, len(deltas) + 1, deltas[0], d[i]))
            i = j + 1
        else:
            i += 1
print("count: %d" % len(found))
for f in sorted(found, key=lambda x: -x[2])[:12]:
    print("   %s +0x%06X  %3d entries  stride %d  first %d" % f)
if found:
    f = sorted(found, key=lambda x: -x[2])[0]
    b = open(os.path.join(RES, f[0]), "rb").read()
    print("\n hexdump of %s +0x%X:" % (f[0], f[1]))
    print(S.dump_at(b, max(0, f[1] - 16), 16 * min(6, (f[1] and 6) or 6)))

print("\n=== 2. fixed-stride array zones (stride 0x20 / 0x30 / 0x88), >=10 elements ===")
zones = []
for m in man:
    b = open(os.path.join(RES, m["resource"]), "rb").read()
    for lag in (0x20, 0x30, 0x40, 0x88):
        best = (0, 0, 0)
        for start in range(0, min(len(b) - 8 * lag, 1 << 16), 4):
            run = 1
            while start + (run + 1) * lag + 8 <= len(b):
                v = struct.unpack_from("<Q", b, start + run * lag)[0]
                if v > 0x10000000000:
                    run += 1
                else:
                    break
            if run > best[0]:
                best = (run, lag, start)
        if best[0] >= 8:
            zones.append((m["resource"], best[2], best[1], best[0]))
print("count: %d" % len(zones))
for z in sorted(zones, key=lambda x: -x[3])[:12]:
    print("   %s +0x%06X  stride 0x%02X  %d hash-like elements" % z)
if zones:
    z = sorted(zones, key=lambda x: -x[3])[0]
    b = open(os.path.join(RES, z[0]), "rb").read()
    print("\n hexdump of %s +0x%X (stride 0x%02X):" % (z[0], z[1], z[2]))
    print(S.dump_at(b, z[1], 16 * 5))

print("\n=== 3. record-0 head of the biggest stitched resource ===")
big = max(man, key=lambda m: m["size"])
b = open(os.path.join(RES, big["resource"]), "rb").read()
print("   %s  size %d  declared_count@0x08 = %s" % (big["resource"], big["size"], big["declared_count_at_0x08"]))
print(S.dump_at(b, 0, 0x50))

print("\n=== 4. P-class (page permutation head) resources in the corpus ===")
cnt = 0
for m in man:
    b = open(os.path.join(RES, m["resource"]), "rb").read()
    for n in (7, 8, 9):
        v = [struct.unpack_from(">H", b, 2 * k)[0] for k in range(n)]
        if sorted(v) == list(range(n)):
            cnt += 1
            print("   %s : N=%d perm=%s at offset 0" % (m["resource"], n, v))
            break
print("   resources with a head permutation: %d" % cnt)

print("\n=== 5. ASCII strings anywhere in the resources (task: ids / names) ===")
strs = collections.Counter()
for m in man:
    b = open(os.path.join(RES, m["resource"]), "rb").read()
    for s in re.findall(rb"[ -~]{6,}", b):
        strs[s] += 1
print("   distinct printable runs >=6: %d" % len(strs))
for s, c in strs.most_common(12):
    print("     %-40r x%d" % (s[:40], c))
