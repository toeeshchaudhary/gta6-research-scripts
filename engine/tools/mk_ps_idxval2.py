import io, os, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'work', 'ps_pc.spvasm')
OUTDIR = os.path.join(ROOT, 'engine', 'shaders', 'gs')
AS = os.path.join(ROOT, 'work', 'spirv', 'spirv-as.exe')
L = io.open(SRC, encoding='utf-8').read().splitlines()

i_comp = max(i for i, l in enumerate(L) if l.strip().startswith('%1297 = OpCompositeConstruct'))
out = list(L)
out[i_comp] = """        %_fi = OpConvertUToF %19 %738
        %_fs = OpConvertUToF %19 %1170
        %1297 = OpCompositeConstruct %20 %_fi %_fs %1295 %_one"""
body = [l for l in out if l != '']
k = next(i for i, l in enumerate(body) if 'OpConstant ' in l)
body = body[:k] + ['        %_one = OpConstant %19 1.0'] + body[k:]
path = os.path.join(OUTDIR, 'dbg_ps_idxval2.spvasm')
io.open(path, 'w', encoding='utf-8').write('\n'.join(body) + '\n')
spv = os.path.join(OUTDIR, 'dbg_ps_idxval2.spv')
r = subprocess.run([AS, '--target-env', 'vulkan1.2', '-o', spv, path], capture_output=True, text=True)
print('as', r.returncode, r.stderr.strip()[:200])
