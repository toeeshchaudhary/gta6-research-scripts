import io, os, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'work', 'ps_pc.spvasm')
OUTDIR = os.path.join(ROOT, 'engine', 'shaders', 'gs')
AS = os.path.join(ROOT, 'work', 'spirv', 'spirv-as.exe')
L = io.open(SRC, encoding='utf-8').read().splitlines()


def build(name, edits):
    out = list(L)
    for pat, rep in edits:
        hit = 0
        for i, l in enumerate(out):
            if l.strip().startswith(pat):
                out[i] = rep
                hit += 1
        assert hit == 1, (name, pat, hit)
    path = os.path.join(OUTDIR, name + '.spvasm')
    io.open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    r = subprocess.run([AS, '--target-env', 'vulkan1.2', '-o', os.path.join(OUTDIR, name + '.spv'), path],
                       capture_output=True, text=True)
    print(name, 'as', r.returncode, r.stderr.strip()[:200])


# image index constant, sampler index still from the lookup
build('dbg_ps_img0', [('%740 = OpAccessChain %55 %5 %738', '        %740 = OpAccessChain %55 %5 %61')])
# sampler index constant, image index still from the lookup
build('dbg_ps_smp0', [('%1172 = OpAccessChain %56 %6 %1170', '        %1172 = OpAccessChain %56 %6 %61')])
