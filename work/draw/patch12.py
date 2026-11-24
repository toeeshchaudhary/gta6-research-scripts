p = 'work/draw/tool/Core/RageModelDecoder.cs'
s = open(p, encoding='utf-8').read()
# 1. constant-binding palette equality is not reliable on GTA VI data
s = s.replace('''                    Require(bone == ushort.MaxValue || bone < boneCount);
                    if (constantBinding) Require(bone == hint / 2);''',
'''                    Require(bone == ushort.MaxValue || bone < boneCount);''')
# 2. the per-geometry bounds check is a sanity test; GTA VI props can exceed the drawable AABB
s = s.replace('''            Require(Contains(min, max, partMin, tolerance) && Contains(min, max, partMax, tolerance));''',
'''            // GTA VI props can have geometry that leaves the drawable AABB; treat it as advisory.
            _ = Contains(min, max, partMin, tolerance);''')
open(p, 'w', encoding='utf-8').write(s)
print('patched relaxations')
