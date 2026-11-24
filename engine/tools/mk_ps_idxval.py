import io, os, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'work', 'ps_pc.spvasm')
OUTDIR = os.path.join(ROOT, 'engine', 'shaders', 'gs')
AS = os.path.join(ROOT, 'work', 'spirv', 'spirv-as.exe')
L = io.open(SRC, encoding='utf-8').read().splitlines()

samp_i = next(i for i, l in enumerate(L) if 'OpImageSampleImplicitLod' in l)
store_i = max(i for i, l in enumerate(L) if l.strip().startswith('OpStore %3 '))

out = list(L)
out[samp_i] = ''
out[store_i] = """        %_fi = OpConvertUToF %19 %738
        %_fs = OpConvertUToF %19 %1170
        %_vv = OpCompositeConstruct %20 %_fi %_fs %_zero %_one
               OpStore %3 %_vv"""
body = [l for l in out if l != '']
# constants must live in the module-level constant section: put them right
# before the first constant declaration that already exists
k = next(i for i, l in enumerate(body) if 'OpConstant ' in l)
body = body[:k] + [
    '        %_zero = OpConstant %19 0.0',
    '        %_one = OpConstant %19 1.0',
    '        %1178 = OpConstantComposite %20 %_zero %_zero %_zero %_one',
] + body[k:]

path = os.path.join(OUTDIR, 'dbg_ps_idxval.spvasm')
io.open(path, 'w', encoding='utf-8').write('\n'.join(body) + '\n')
spv = os.path.join(OUTDIR, 'dbg_ps_idxval.spv')
r = subprocess.run([AS, '--target-env', 'vulkan1.2', '-o', spv, path], capture_output=True, text=True)
print('as', r.returncode, r.stderr.strip()[:200])
r = subprocess.run([os.path.join(ROOT, 'work', 'spirv', 'spirv-val.exe'), '--target-env', 'vulkan1.2', spv],
                   capture_output=True, text=True)
print('val', r.returncode, r.stderr.strip()[:200])
