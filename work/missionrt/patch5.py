import sys

h = r"src/missionrt.h"
s = open(h, encoding="utf-8").read()
s = s.replace("    std::vector<uint32_t> dwords;  // raw slice, kept so nothing is lost",
              "    std::vector<uint32_t> dwords;  // raw slice, kept so nothing is lost\n"
              "    std::string readTag;           // which offset reading produced the entities")
open(h, "w", encoding="utf-8").write(s)

c = r"src/missionrt.cpp"
s = open(c, encoding="utf-8").read()
s = s.replace('                readDwords(rv.get("dwords"), r.dwords);',
              '                readDwords(rv.get("dwords"), r.dwords);\n'
              '                if (const mrjson::Value* rd = rv.get("readings"))\n'
              '                    if (rd->isArr())\n'
              '                        for (size_t k = 0; k < rd->arr.size(); ++k)\n'
              '                            r.readTag += (k ? "," : "") + rd->arr[k].string();')
open(c, "w", encoding="utf-8").write(s)

r = r"src/missionrun.cpp"
s = open(r, encoding="utf-8").read()
s = s.replace('                if (r.poolTag) line += " pool=" + hex8(r.poolTag);\n'
              '                if (!r.inBounds) line += " OUT_OF_SLICE";',
              '                if (r.poolTag) line += " pool=" + hex8(r.poolTag);\n'
              '                if (!r.inBounds) line += " pool_oob";\n'
              '                if (!r.readTag.empty()) line += " read=" + r.readTag;')
s = s.replace('"\\"row\\": %u, \\"in_bounds\\": %s, \\"payload\\": \\"%s\\", \\"entities\\": [",',
              '"\\"row\\": %u, \\"in_bounds\\": %s, \\"readings\\": \\"%s\\", \\"payload\\": \\"%s\\", "\n'
              '                        "\\"entities\\": [",')
s = s.replace('r.inBounds ? "true" : "false",\n                        r.payload == PAY_ENTITY',
              'r.inBounds ? "true" : "false", r.readTag.c_str(),\n                        r.payload == PAY_ENTITY')
open(r, "w", encoding="utf-8").write(s)
print("patched")
