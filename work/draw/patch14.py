p = 'work/draw/tool/Core/RageModelDecoder.cs'
s = open(p, encoding='utf-8').read()
s = s.replace("            bool bonePalette = (countFlags & 0x40000000) != 0;",
              "            bool bonePalette = (countFlags & 0xC0000000) != 0;")
s = s.replace("            uint binding = U32(sys, descriptor + 12);",
              "            uint binding = U32(sys, descriptor + 12);")
s = s.replace("""            Require(clusterCount is > 0 and <= 2048 && triangles is > 0 and <= 65535 && refs is > 0 and <= 65535 &&""",
              """            Require(clusterCount is > 0 and <= 2048 && triangles is > 0 && <= 65535 && refs is > 0 && <= 65535 &&""")
s = s.replace("""                refs == ((binding >> 8) & 0x7FFFFF) && ((binding & 0x80000000) != 0) == bonePalette &&
                (!bonePalette || (binding & 255) == 0x80U));""",
              """                refs == ((binding >> 8) & 0x7FFFFF));""")
s = s.replace("            int refSize = (countFlags & 0x80000000) != 0 ? 2 : 4;",
              "            int refSize = (binding & 0x80000000) != 0 ? 2 : 4;")
open(p, 'w', encoding='utf-8').write(s)
print('patch14')
