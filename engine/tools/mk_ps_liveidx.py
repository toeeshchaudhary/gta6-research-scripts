import io, os, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'work', 'ps_pc.spvasm')
OUTDIR = os.path.join(ROOT, 'engine', 'shaders', 'gs')
AS = os.path.join(ROOT, 'work', 'spirv', 'spirv-as.exe')
L = io.open(SRC, encoding='utf-8').read().splitlines()

i_ac = next(i for i, l in enumerate(L) if l.strip().startswith('%740 = OpAccessChain'))
i_comp = max(i for i, l in enumerate(L) if l.strip().startswith('%1297 = OpCompositeConstruct'))
out = list(L)
# constant index, but keep the lookup result live by writing it into R
out[i_ac] = '        %740 = OpAccessChain %55 %5 %61'
out[i_comp] = """        %_fi = OpConvertUToF %19 %738
        %1297 = OpCompositeConstruct %20 %_fi %1291 %1295 %_one"""
body = [l for l in out if l != '']
k = next(i for i, l in enumerate(body) if 'OpConstant ' in l)
body = body[:k] + ['        %_one = OpConstant %19 1.0'] + body[k:]
path = os.path.join(OUTDIR, 'dbg_ps_liveidx.spvasm')
io.open(path, 'w', encoding='utf-8').write('\n'.join(body) + '\n')
spv = os.path.join(OUTDIR, 'dbg_ps_liveidx.spv')
r = subprocess.run([AS, '--target-env', 'vulkan1.2', '-o', spv, path], capture_output=True, text=True)
print('as', r.returncode, r.stderr.strip()[:200])
