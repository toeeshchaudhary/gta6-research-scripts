import struct, collections, math, json, sys
import an2

def load_decls():
    d = {}
    for line in open(r"../../work/arch/dict/resnames_full.tsv", encoding="utf-8", errors="replace"):
        if line.startswith("#"): continue
        p = line.rstrip("\n").split("\t")
        if len(p) < 4: continue
        try: off = int(p[0], 16)
        except: continue
        h = None
        if p[2].startswith("0x"):
            try: h = int(p[2], 16)
            except: h = None
        d[off] = (p[1], h, p[3])
    return d

def joaat(s):
    h = 0
    for ch in s.lower():
        h = (h + ord(ch)) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF

def main():
    T = an2.merge(an2.load_tables())
    M = [(res, n, body) for res, start, n, kind, body in T if kind == 1]
    print("M tables:", len(M), "records", sum(t[1] for t in M))

    decl = load_decls()
    # M resource root-position sanity
    farroot = 0
    named = 0
    per_res_names = {}
    for res, n, body in M:
        p0 = struct.unpack("<3f", body[0:12])
        if max(abs(p0[0]), abs(p0[1]), abs(p0[2])) > 1000: farroot += 1
        d = decl.get(res)
        if d:
            named += 1
            per_res_names.setdefault(res, []).append(d)
    print("M resources with a self-declaration name:", named, "/", len(M))
    print("M tables whose ROOT record is at |pos|>1000 (already world-space):", farroot)

    # id index over W records
    ids = collections.defaultdict(list)
    for res, start, n, kind, body in T:
        if kind != 0: continue
        for i in range(n):
            r = body[i*80:(i+1)*80]
            pos = struct.unpack("<3f", r[0:12]); yaw = struct.unpack("<f", r[12:16])[0]
            for k in range(4):
                h = struct.unpack("<I", r[0x20 + 4*k:0x24 + 4*k])[0]
                ids[h].append((res, pos, yaw, k))
    print("distinct W id values:", len(ids))

    hits = 0; multi = 0; samples = []
    for res, lst in per_res_names.items():
        name, h, tag = lst[0]
        if h is None: h = joaat(name)
        if h in ids:
            hits += 1
            if len(ids[h]) > 1: multi += 1
            if len(samples) < 15:
                samples.append((res, name, len(ids[h]), ids[h][:2]))
    print("M resources whose archetype hash is placed in the world:", hits, "/", len(per_res_names))
    print("  of those, placed more than once:", multi)
    for res, name, n, ex in samples:
        print("  0x%X %-50s placements=%d %s" % (res, name, n, [(hex(r), p, round(y,2), k) for r,p,y,k in ex]))
    json.dump({hex(r): n for r, n, _, _ in [(r, len(ids[joaat(d[0][0])]) if joaat(d[0][0]) in ids else 0, 0, 0) for r, d in per_res_names.items()]},
              open("out/mparent.json", "w"), indent=0)

if __name__ == "__main__":
    main()
