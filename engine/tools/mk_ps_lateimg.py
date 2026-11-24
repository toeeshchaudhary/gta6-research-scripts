import io, os, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'work', 'ps_pc.spvasm')
OUTDIR = os.path.join(ROOT, 'engine', 'shaders', 'gs')
AS = os.path.join(ROOT, 'work', 'spirv', 'spirv-as.exe')
L = io.open(SRC, encoding='utf-8').read().splitlines()

i_si = next(i for i, l in enumerate(L) if l.strip().startswith('%1174 = OpSampledImage'))
out = list(L)
out[i_si] = """        %_ac = OpAccessChain %55 %5 %738
        %_im = OpLoad %47 %_ac
        %1174 = OpSampledImage %49 %_im %1173"""
path = os.path.join(OUTDIR, 'dbg_ps_lateimg.spvasm')
io.open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
spv = os.path.join(OUTDIR, 'dbg_ps_lateimg.spv')
r = subprocess.run([AS, '--target-env', 'vulkan1.2', '-o', spv, path], capture_output=True, text=True)
print('as', r.returncode, r.stderr.strip()[:200])
