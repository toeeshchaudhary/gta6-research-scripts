"""step12_verify.py - verification with a null model, resource export, and content hunt.

  A. absolute target lattice: where do pointer targets sit mod 0x88 / 0x10? (base lattice)
  B. null model: is the greedy content stitch better than random chunk order?
  C. export every stitched resource to work/stitch/resources with a manifest
  D. content-of-interest hunt inside stitched resources
"""
import json, os, sys, struct, collections, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stitchlib as S

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "resources")
os.makedirs(RES, exist_ok=True)
meta = sorted(json.load(open(os.path.join(HERE, "streams_meta.json"))), key=lambda s: s["off"])
res = json.load(open(os.path.join(HERE, "resources.json")))


def plaintext(off):
    for fam, d in (("exact", r"work\codec\full\exact"), ("zd", r"work\codec\full\zeros_dict_unverified")):
        p = os.path.join(S.ROOT, d, "%s_%08X.bin" % (fam, off))
        if os.path.exists(p):
            return open(p, "rb").read()
    r = S.inflate(off)
    return r["out"] if r else b""


CH = {s["off"]: plaintext(s["off"]) for s in meta}
ORDER = [s["off"] for s in meta]


def elem_score(b, p, n=4):
    if p < 0 or p + 4 * n > len(b):
        return 0.0
    v = struct.unpack_from("<%dI" % n, b, p)
    ok = 0.0
    for x in v:
        if 0 < x < 0x100000:
            ok += 1
        elif x in (0, 0xFFFFFFFF):
            ok += 0.3
        elif 0x50000000 <= x <= 0x50FFFFFF:
            ok += 0.5
    return ok / n


# ---------- A. target lattice ------------------------------------------------------
print("=== A. absolute pointer-target residues (all 13,461 targets) ===")
allt = [t for o in ORDER for _, _, t in S.ptr_offsets(CH[o])]
c16 = collections.Counter(t % 16 for t in allt)
c88 = collections.Counter(t % 0x88 for t in allt)
print("  mod 16:", sorted(c16.items()))
print("  mod 0x88 top 10:", c88.most_common(10))
slot_hit = sum(v for k, v in c88.items() if k in (0x28, 0x50, 0x58, 0x60))
print("  targets on a record slot residue {0x28,0x50,0x58,0x60}: %d / %d = %.3f (chance 0.118)"
      % (slot_hit, len(allt), slot_hit / len(allt)))
print("  mod 16 == 0: %.3f (chance 0.0625)" % (c16[0] / len(allt)))

# ---------- B. null model ---------------------------------------------------------
print("\n=== B. null model: greedy content order vs random order ===")
rng = random.Random(11)
multi = [r for r in res if len(r["chain"]) > 1]
rows = []
for r in multi:
    head, chain = r["head"], r["chain"]
    targets = [t for _, _, t in S.ptr_offsets(CH[head])]
    buf0 = CH[head]
    tail = [o for o in chain[1:]]
    variants = []
    for trial in range(200):
        rng.shuffle(tail)
        buf = buf0 + b"".join(CH[o] for o in tail)
        inside = [t for t in targets if t + 4 < len(buf)]
        if not inside:
            continue
        variants.append(sum(elem_score(buf, t) for t in inside) / len(inside))
    if not variants:
        continue
    variants.sort()
    obs = r["array_score"]
    pct = sum(1 for v in variants if v < obs) / len(variants)
    rows.append((head, len(chain), obs, variants[len(variants) // 2], variants[int(0.95 * len(variants))], pct))
print("  head       nchunks  greedy_score  null_median  null_p95  percentile")
for x in sorted(rows, key=lambda x: -x[5]):
    print("  0x%08X %4d      %.3f        %.3f      %.3f     %.2f" % x)
if rows:
    print("  mean greedy %.3f ; mean null median %.3f ; resources above null p95: %d/%d" % (
        sum(x[2] for x in rows) / len(rows), sum(x[3] for x in rows) / len(rows),
        sum(1 for x in rows if x[5] >= 0.95), len(rows)))

# ---------- C. export -------------------------------------------------------------
print("\n=== C. exporting resources ===")
manifest = []
for r in res:
    buf = b"".join(CH[o] for o in r["chain"])
    name = "res_%08X.bin" % r["head"]
    open(os.path.join(RES, name), "wb").write(buf)
    nrec = len(buf) // 0x88
    tr = [t for _, _, t in S.ptr_offsets(buf)]
    inside = [t for t in tr if t + 4 < len(buf)]
    manifest.append({
        "resource": name, "head_chunk": "0x%08X" % r["head"], "chunks": r["chain"],
        "n_chunks": len(r["chain"]), "size": len(buf), "records_0x88": nrec,
        "pointers": len(tr), "targets_inside": len(inside),
        "frac_inside": round(len(inside) / len(tr), 4) if tr else None,
        "array_score": round(sum(elem_score(buf, t) for t in inside) / len(inside), 3) if inside else None,
        "declared_count_at_0x08": struct.unpack_from("<I", buf, 8)[0] if len(buf) > 16 else None,
        "source_archive": "story000_script.rpf",
    })
json.dump(manifest, open(os.path.join(RES, "manifest.json"), "w"), indent=1)
print("  %d files written to %s" % (len(manifest), RES))
print("  total bytes: %d" % sum(m["size"] for m in manifest))
print("  multi-chunk: %d" % sum(1 for m in manifest if m["n_chunks"] > 1))

# ---------- D. content hunt ------------------------------------------------------
print("\n=== D. content hunt in stitched resources ===")
print("  D1. ascending u32 tables with small constant stride (index tables / switch candidates)")
hits = []
for m in manifest:
    b = open(os.path.join(RES, m["resource"]), "rb").read()
    d = struct.unpack_from("<%dI" % (len(b) // 4), b, 0)
    i = 0
    while i < len(d) - 8:
        j = i
        while j + 1 < len(d) and 0 < d[j + 1] - d[j] < 0x100 and d[j + 1] > d[j]:
            j += 1
        if j - i >= 6:
            st = d[i + 1] - d[i]
            if all(d[i + k + 1] - d[i + k] == st for k in range(j - i)):
                hits.append((m["resource"], i * 4, j - i + 1, st, d[i]))
            i = j + 1
        else:
            i += 1
print("     constant-stride ascending tables: %d" % len(hits))
for h in hits[:14]:
    print("       %s +0x%06X  %d entries  stride %d  first %d" % h)

print("  D2. (offset,size) pair tables: runs of ascending 4K-ish offsets followed by sizes")
pairhits = []
for m in manifest:
    b = open(os.path.join(RES, m["resource"]), "rb").read()
    d = struct.unpack_from("<%dI" % (len(b) // 4), b, 0)
    for i in range(0, len(d) - 8, 2):
        a0, s0, a1, s1 = d[i], d[i + 1], d[i + 2], d[i + 3]
        if 0x100 <= a0 < a1 and a1 - a0 < 0x20000 and 0 < s0 < a1 - a0 + 1 and 0 < s1 < 0x20000:
            pairhits.append((m["resource"], i * 4, a0, s0, a1, s1))
print("     candidate (offset,size) pairs: %d" % len(pairhits))
for p in pairhits[:6]:
    print("       %s +0x%06X  (%d,%d) (%d,%d)" % p)

print("  D3. cross-chunk 64-bit hash references inside a single stitched resource")
xref = 0
for m in manifest:
    if m["n_chunks"] < 2:
        continue
    b = open(os.path.join(RES, m["resource"]), "rb").read()
    seen = collections.Counter()
    for p in range(0, len(b) - 8, 8):
        v = struct.unpack_from("<Q", b, p)[0]
        if v > 0x10000000000:
            seen[v] += 1
    rep = sum(1 for v, c in seen.items() if c > 1)
    xref += rep
print("     hash values occurring more than once inside one resource: %d" % xref)
