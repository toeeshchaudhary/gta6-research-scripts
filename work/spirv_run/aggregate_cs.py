"""Aggregate every compute row we have into one table + failure taxonomy + user-SGPR cross-tab.

Inputs:  logs_cs\\rows*.jsonl (translation rows), logs_cs\\tax*.jsonl (per-shader taxonomy sidecar),
         hdr_info.jsonl (COMPUTE_PGM_RSRC2 per blob), cs_fssm\\ names (the universe).
Output:  stdout summary + cs_summary.json
"""
import glob
import collections
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RANK_OK = 4  # how far a row got: 1=disasm only, 2=translated, 3=assembled, 4=validated


def rank(r):
    if r.get("val13_ok") or r.get("val_ok"):
        return 4
    if r.get("as_ok"):
        return 3
    if r.get("spirv_ok"):
        return 2
    return 1


def load_rows():
    rows = {}
    src = {}
    for f in sorted(glob.glob(os.path.join(HERE, "logs_cs", "rows*.jsonl"))):
        for l in open(f, encoding="utf-8", errors="replace"):
            l = l.strip()
            if not l:
                continue
            try:
                r = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            n = r.get("name")
            if not n or r.get("stage") not in ("cs", "?"):
                continue
            if n not in rows or rank(r) > rank(rows[n]):
                rows[n] = r
                src[n] = os.path.basename(f)
    return rows, src


def load_tax():
    tax = {}
    for f in sorted(glob.glob(os.path.join(HERE, "logs_cs", "tax*.jsonl"))):
        for l in open(f, encoding="utf-8", errors="replace"):
            l = l.strip()
            if not l:
                continue
            try:
                r = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            n = r.get("name")
            if n and n not in tax:
                tax[n] = r
    return tax


def load_hdr():
    h = {}
    for l in open(os.path.join(HERE, "hdr_info.jsonl"), encoding="utf-8"):
        r = json.loads(l)
        h[r["name"]] = r
    return h


def norm_err(e):
    if not e:
        return None
    e = e.strip()
    for pre in ("val1.2: ", "val1.3: ", "as: ", "unsupported: ", "disasm: "):
        if e.startswith(pre):
            return pre.rstrip(": ") + " | " + e[len(pre):][:90]
    return e[:110]


def main():
    universe = sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(HERE, "cs_fssm"))
                      if f.endswith(".fssm"))
    rows, src = load_rows()
    tax = load_tax()
    hdr = load_hdr()
    spv = [os.path.splitext(f)[0] for f in os.listdir(os.path.join(HERE, "cs_spirv"))
           if f.endswith(".spv")]
    spvset = set(spv)

    U = set(universe)
    inU = [n for n in rows if n in U]
    counts = collections.Counter()
    counts["universe"] = len(universe)
    counts["rows"] = len(inU)
    counts["no_row"] = len(U - set(rows))
    counts["spv_files"] = len(spvset)
    counts["spv_no_row"] = len(spvset - set(rows))
    for r in (rows[n] for n in inU):
        counts["spirv_ok"] += bool(r.get("spirv_ok"))
        counts["as_ok"] += bool(r.get("as_ok"))
        counts["val_ok"] += bool(r.get("val_ok"))
        counts["val13_ok"] += bool(r.get("val13_ok"))
        counts["wave64"] += bool(r.get("wave64"))
    counts["disassembled"] = sum(1 for n in inU if not str(rows[n].get("error") or "").startswith(
        "disasm:"))
    counts["disasm_fail"] = sum(1 for n in inU if str(rows[n].get("error") or "").startswith(
        "disasm:"))

    errs = collections.Counter(norm_err(rows[n].get("error")) for n in inU if rows[n].get("error"))
    kinds = collections.Counter(tax.get(n, {}).get("kind") for n in inU)
    disasm_kinds = collections.Counter(tax.get(n, {}).get("disasm") for n in inU)

    # ---- cross-tab: does the shader read a launch-time SGPR that the 32-slot user-data model misrepresents?
    xt = collections.Counter()
    for n in inU:
        r, t, h = rows[n], tax.get(n, {}), hdr.get(n, {})
        ok = bool(r.get("val_ok"))
        u = h.get("user_sgprs")
        early = t.get("early_slots") or []
        sys_reads = [s for s in early if u is not None and s >= u]
        key = (ok, bool(early), bool(sys_reads), h.get("tgid_en"), u)
        xt[key] += 1

    # ---- among FAILURES only: how many depend on launch-time SGPR setup at all?
    fail = [n for n in inU if not rows[n].get("val_ok")]
    dep = collections.Counter()
    for n in fail:
        t, h = tax.get(n, {}), hdr.get(n, {})
        early = t.get("early_slots") or []
        u = h.get("user_sgprs")
        dep["fail"] += 1
        dep["fail_with_early_user_read"] += bool(early)
        dep["fail_with_system_sgpr_read"] += bool(u is not None and [s for s in early if s >= u])
        dep["fail_tg_size_en"] += bool(h.get("tg_size_en"))
        dep["fail_no_user_read"] += not early
    summary["failure_dependence"] = dict(dep)

    summary = {
        "counts": dict(counts),
        "errors": errs.most_common(30),
        "kinds": dict(kinds),
        "disasm": dict(disasm_kinds),
    }
    # ---- timings actually spent (only rows that carry a taxonomy row measure it)
    tt = collections.Counter()
    for n in inU:
        t = tax.get(n, {})
        tt["disasm"] += t.get("t_disasm") or 0
        tt["trans"] += t.get("t_trans") or 0
        tt["tax"] += t.get("t_tax") or 0
        tt["asval"] += t.get("t_asval") or 0
    summary["seconds"] = dict(tt)
    summary["timed_rows"] = sum(1 for n in inU if tax.get(n, {}).get("t_trans"))
    print(json.dumps({k: summary[k] for k in ("counts",)}, indent=1))
    print("\n-- outcome kinds (tax):", dict(kinds))
    print("-- disasm results:", dict(disasm_kinds))
    print("\n-- top error strings:")
    for e, c in errs.most_common(25):
        print("%6d  %s" % (c, e))
    print("\n-- val_ok x (reads user-slot-before-write) x (reads slot >= declared USER_SGPR) x tgid_en:")
    agg = collections.Counter()
    for (ok, early, sysr, tg, u), c in xt.items():
        agg[(ok, early, sysr, tg)] += c
    for k in sorted(agg, key=lambda k: (-agg[k])):
        print("  val_ok=%s early=%s sysread=%s tgid_en=%s  %d" % (k[0], k[1], k[2], k[3], agg[k]))
    print("\n-- declared USER_SGPR count vs validation:")
    byu = collections.Counter((hdr.get(n, {}).get("user_sgprs"), bool(rows[n].get("val_ok")))
                              for n in inU)
    for u in sorted({k[0] for k in byu}, key=lambda x: (x is None, x)):
        print("  user_sgprs=%s  fail=%d ok=%d" % (u, byu.get((u, False), 0), byu.get((u, True), 0)))
    with open(os.path.join(HERE, "cs_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print("\nsaved cs_summary.json")
    print("-- seconds:", dict(tt), "over", summary["timed_rows"], "timed rows")


if __name__ == "__main__":
    main()
