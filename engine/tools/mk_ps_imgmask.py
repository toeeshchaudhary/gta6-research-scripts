import io, os, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'work', 'ps_pc.spvasm')
OUTDIR = os.path.join(ROOT, 'engine', 'shaders', 'gs')
AS = os.path.join(ROOT, 'work', 'spirv', 'spirv-as.exe')
L = io.open(SRC, encoding='utf-8').read().splitlines()

i_ac = next(i for i, l in enumerate(L) if l.strip().startswith('%740 = OpAccessChain'))
out = list(L)
out[i_ac] = """        %_m = OpBitwiseAnd %17 %738 %62
        %740 = OpAccessChain %55 %5 %_m"""
path = os.path.join(OUTDIR, 'dbg_ps_imgmask.spvasm')
io.open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
spv = os.path.join(OUTDIR, 'dbg_ps_imgmask.spv')
r = subprocess.run([AS, '--target-env', 'vulkan1.2', '-o', spv, path], capture_output=True, text=True)
print('as', r.returncode, r.stderr.strip()[:200])
