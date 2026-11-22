"""M4 task 1+2: join scene_world.json instances to arch_model.json, then find the densest region.

Writes:
  engine/out/m4_join.json      join statistics
  engine/out/m4_region.json    the chosen region (bounds, instance list with bound obj files)
  engine/out/m4_models.tsv     per-model bounds/verts/tris for the models the region needs
"""
import json, os, sys, collections, math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCENE = os.path.join(ROOT, 'work', 'world', 'scene_world.json')
ARCH = os.path.join(ROOT, 'work', 'draw', 'out', 'arch_model.json')
MANIFEST = os.path.join(ROOT, 'work', 'draw', 'out', 'manifest.tsv')
OUT = os.path.join(ROOT, 'engine', 'out')
os.makedirs(OUT, exist_ok=True)

print('loading arch_model.json ...', flush=True)
arch = json.load(open(ARCH, encoding='utf-8'))
rows = arch['bindings'] if isinstance(arch, dict) and 'bindings' in arch else arch
print('bindings:', len(rows), flush=True)
by_hash = {}
for r in rows:
    h = int(r['archetype_hash'], 16) & 0xFFFFFFFF
    by_hash.setdefault(h, []).append(r)

print('loading manifest bounds ...', flush=True)
bounds = {}
nv = 0
with open(MANIFEST, encoding='utf-8', errors='replace') as f:
    for line in f:
        if line.startswith('#'):
            continue
        p = line.rstrip('\n').split('\t')
        if len(p) < 8 or p[3] != 'ok':
            continue
        obj = p[6]
        det = p[7]
        i = det.find('bounds ')
        bb = None
        if i >= 0:
            s = det[i + 7:].split('meshes')[0]
            try:
                lo, hi = s.split('..')
                l = [float(x) for x in lo.strip().split(',')]
                hh = [float(x) for x in hi.strip().split(',')]
                bb = (min(l[0], hh[0]), min(l[1], hh[1]), min(l[2], hh[2]),
                      max(l[0], hh[0]), max(l[1], hh[1]), max(l[2], hh[2]))
            except Exception:
                bb = None
        bounds[obj] = bb
        bounds[os.path.basename(obj)] = bb
print('manifest ok rows:', len(bounds), 'with bounds:', sum(1 for v in bounds.values() if v), flush=True)

print('loading scene ...', flush=True)
scene = json.load(open(SCENE, encoding='utf-8'))
inst = scene['instances']
print('instances:', len(inst), flush=True)

resolved = []
res_by_hash = collections.Counter()
unres_hashes = collections.Counter()
for i, ins in enumerate(inst):
    h = int(ins['hash'], 16) & 0xFFFFFFFF
    cand = by_hash.get(h)
    if not cand:
        unres_hashes[h] += 1
        continue
    r = cand[0]
    if r['obj_file'] not in bounds or bounds[r['obj_file']] is None:
        unres_hashes[h] += 1
        continue
    resolved.append((i, ins, r))
    res_by_hash[h] += 1

n = len(inst)
print('resolved instances: %d / %d = %.3f%%' % (len(resolved), n, 100.0 * len(resolved) / n))
print('resolved distinct hashes: %d / %d' % (len(res_by_hash), len(set((int(x['hash'],16)&0xFFFFFFFF) for x in inst))))
print('unresolved distinct hashes:', len(unres_hashes))
print('top unresolved:')
for h, c in unres_hashes.most_common(12):
    print('  0x%08x  %d' % (h, c))

# spatial clustering on a 200-unit grid over x,y (z is height? check extents)
xs = [ins['pos'][0] for _, ins, _ in resolved]
ys = [ins['pos'][1] for _, ins, _ in resolved]
zs = [ins['pos'][2] for _, ins, _ in resolved]
print('resolved pos extents x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f' % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
axs = [ins['pos'][0] for ins in inst]
ays = [ins['pos'][1] for ins in inst]
azs = [ins['pos'][2] for ins in inst]
print('all pos extents      x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f' % (min(axs), max(axs), min(ays), max(ays), min(azs), max(azs)))

GRID = 200.0
cell_res = collections.Counter()
cell_all = collections.Counter()
cellmod = collections.defaultdict(set)
for i, ins, r in resolved:
    k = (int(math.floor(ins['pos'][0] / GRID)), int(math.floor(ins['pos'][1] / GRID)))
    cell_res[k] += 1
    cellmod[k].add(r['obj_file'])
for ins in inst:
    k = (int(math.floor(ins['pos'][0] / GRID)), int(math.floor(ins['pos'][1] / GRID)))
    cell_all[k] += 1
print('\ndensest 200-unit cells (resolved count):')
for k, c in cell_res.most_common(15):
    print('  cell %s  resolved %4d  all %4d  models %2d' % (k, c, cell_all[k], len(cellmod[k])))

# choose densest cell, then expand by one cell in each direction to make a block-sized region
best = cell_res.most_common(1)[0][0]
blocks = [(x, y, 1, 1, 0, None)]
# try region sizes 1,2,3 cells and score by resolved*models
bestcfg = None
for w in (1, 2, 3, 4, 5):
    for dx in range(-(w - 1), 1):
        for dy in range(-(w - 1), 1):
            x0, y0 = best[0] + dx, best[1] + dy
            cnt = 0
            ms = set()
            for cx in range(x0, x0 + w):
                for cy in range(y0, y0 + w):
                    cnt += cell_res[(cx, cy)]
                    ms |= cellmod[(cx, cy)]
            if cnt == 0:
                continue
            score = cnt * (len(ms) ** 0.5)
            if bestcfg is None or score > bestcfg[0]:
                bestcfg = (score, w, x0, y0, cnt, ms)
print('\nbest region: honour score, cells w=%d at (%d,%d) resolved=%d models=%d' % (bestcfg[1], bestcfg[2], bestcfg[3], bestcfg[4], len(bestcfg[5])))
_, w, x0, y0, cnt, ms = bestcfg

bx0, by0 = x0 * GRID, y0 * GRID
bx1, by1 = (x0 + w) * GRID, (y0 + w) * GRID
region = [t for t in resolved if bx0 <= t[1]['pos'][0] < bx1 and by0 <= t[1]['pos'][1] < by1]
print('region bounds x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f  instances %d'
      % (bx0, bx1, by0, by1, min(t[1]['pos'][2] for t in region), max(t[1]['pos'][2] for t in region), len(region)))

models = collections.Counter(t[2]['obj_file'] for t in region)
print('distinct models in region:', len(models))
for m, c in models.most_common(20):
    print('  %5d  %s' % (c, m))

# write region scene json in a shape our loader will read
out_inst = []
for i, ins, r in region:
    out_inst.append({
        'hash': ins['hash'],
        'model': r['obj_file'],
        'name': r['name'],
        'pos': ins['pos'],
        'rot': ins['rot'],
        'scale': ins['scale'],
        'bounds': list(bounds[r['obj_file']]),
        'verts': r.get('verts'), 'tris': r.get('tris'),
    })
json.dump({'note': 'M4 region: resolved instances only', 'bounds': [bx0, bx1, by0, by1],
           'instances': out_inst}, open(os.path.join(OUT, 'm4_region.json'), 'w'), indent=1)
print('wrote out/m4_region.json', len(out_inst))
