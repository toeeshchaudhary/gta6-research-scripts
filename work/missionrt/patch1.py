import io
p = r"src/missionrt.cpp"
s = open(p, encoding="utf-8").read()
s = s.replace("    uint32_t unknownMembers = 0;", "    uint32_t unknownMembers = 0, zeroKeys = 0;")
old = ('    if (unknownMembers)\n'
       '        warn.push_back("dropped " + std::to_string(unknownMembers) + " entity without position");')
new = old + ('\n    if (zeroKeys)\n'
             '        warn.push_back(std::to_string(zeroKeys) +'
             ' " records have key 0 (continuation slots of a multi-slot item, they join state 00000000)");')
assert old in s, "anchor missing"
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("patched")
