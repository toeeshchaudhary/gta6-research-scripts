import io

# 1) decoder: in_bounds should mean "the element-sized head of the slice is inside the pool"
q = r"p_mr11_decode.py"
t = open(q, encoding="utf-8").read()
old = '                inb = bool(pool) and lim and (pool["off"] + r["ofs"] + 4 * min(r["n"], SLICE_CAP)) <= lim'
new = '                inb = bool(pool) and bool(lim) and (pool["off"] + r["ofs"] + 64) <= lim'
assert old in t
t = t.replace(old, new)
open(q, "w", encoding="utf-8").write(t)

# 2) analyse: report the state count properly
p = r"src/missionrt.cpp"
s = open(p, encoding="utf-8").read()
s = s.replace("void analyse(const Mission& m, std::map<std::string, uint32_t>& stats) {",
              "void analyse(const Mission& m, std::map<std::string, uint32_t>& stats) {\n"
              "    stats[\"states\"] = (uint32_t)m.states.size();")
s = s.replace('    ++stats["states"];\n', "")
open(p, "w", encoding="utf-8").write(s)
print("patched")
