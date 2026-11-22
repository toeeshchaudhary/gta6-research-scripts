import io, os, re, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'work', 'ps_pc.spvasm')
OUTDIR = os.path.join(ROOT, 'engine', 'shaders', 'gs')
AS = os.path.join(ROOT, 'work', 'spirv', 'spirv-as.exe')
VAL = os.path.join(ROOT, 'work', 'spirv', 'spirv-val.exe')

L = io.open(SRC, encoding='utf-8').read().splitlines()
loads = [(i, l) for i, l in enumerate(L) if re.search(r'OpLoad %17 %\d+ Aligned 4', l)]
assert len(loads) == 8, len(loads)
samp_i = next(i for i, l in enumerate(L) if 'OpImageSampleImplicitLod' in l)


def emit_variant(name, kill_sample, kill_heap, tvals):
    out = list(L)
    newconsts = []
    if kill_sample:
        out[samp_i] = ''
        for tag, v in (('_c1', '0.25'), ('_c2', '0.5'), ('_c3', '0.75'), ('_c4', '1.0')):
            newconsts.append('        %%%s = OpConstant %%19 %s' % (tag, v))
        newconsts.append('        %_col = OpConstantComposite %20 %_c1 %_c2 %_c3 %_c4')
    if kill_heap:
        for n, (i, line) in enumerate(loads):
            rid = re.match(r'\s*%(\d+) =', line).group(1)
            out[i] = ''
            newconsts.append('        %%%s = OpConstant %%17 %d' % (rid, tvals[n]))
    if kill_sample:
        # fix up the sample result id reference
        out = [l if '%1178' not in l else l.replace('%1178', '%_col') for l in out]
    body = [l for l in out if l != '']
    ins = next(i for i, l in enumerate(body) if '= OpFunction ' in l)
    body = body[:ins] + newconsts + body[ins:]
    path = os.path.join(OUTDIR, name + '.spvasm')
    io.open(path, 'w', encoding='utf-8').write('\n'.join(body) + '\n')
    spv = os.path.join(OUTDIR, name + '.spv')
    r = subprocess.run([AS, '--target-env', 'vulkan1.2', '-o', spv, path], capture_output=True, text=True)
    print(name, 'as', r.returncode, r.stderr.strip()[:300])
    r = subprocess.run([VAL, '--target-env', 'vulkan1.2', spv], capture_output=True, text=True)
    print(name, 'val', r.returncode, r.stderr.strip()[:400])


emit_variant('dbg_ps_nosample', True, False, None)
emit_variant('dbg_ps_noheap', True, True, [0x14500000, 0xC00000, 0x92, 0, 0, 0, 0, 0])
