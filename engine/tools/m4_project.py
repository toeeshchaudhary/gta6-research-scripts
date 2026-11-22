"""Project instances of a scene through the same VP the engine builds and report
where they should land in NDC. Used to check framing without a viewer.

python m4_project.py <scene.json> <eye x,y,z> <look x,y,z> [--all]
"""
import json, math, sys

sc = json.load(open(sys.argv[1], encoding='utf-8'))
eye = [float(v) for v in sys.argv[2].split(',')]
look = [float(v) for v in sys.argv[3].split(',')]
show_all = '--all' in sys.argv
W, H, FOV = 1280, 720, 0.86

def sub(a, b): return [a[i] - b[i] for i in range(3)]
def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def norm(a):
    l = math.sqrt(sum(v*v for v in a)) or 1e-9
    return [v/l for v in a]
def dot(a, b): return sum(a[i]*b[i] for i in range(3))

f = norm(sub(look, eye))
up = [0.0, 0.0, 1.0]
s = norm(cross(f, up))
u = cross(s, f)
aspect = W / H
ftan = 1.0 / math.tan(FOV * 0.5)

def proj(p):
    d = sub(p, eye)
    x, y, z = dot(d, s), dot(d, u), -dot(d, f)  # lookAt frame
    depth = -z
    if depth <= 0.001:
        return None
    cx = (ftan / aspect) * x
    cy = -ftan * y
    cw = depth
    return (cx / cw, cy / cw, cw)

bounds = sc.get('bounds')
print('scene bounds', bounds, 'instances', len(sc['instances']))
onscreen = 0
for i in sc['instances']:
    p = i['pos']
    if not show_all and i.get('tag') == 'car':
        continue
    r = proj(p)
    if r is None:
        continue
    nx, ny, cw = r
    if -1 <= nx <= 1 and -1 <= ny <= 1:
        onscreen += 1
    # ndc -> pixel
    px = int((nx * 0.5 + 0.5) * W)
    py = int((ny * 0.5 + 0.5) * H)
    print('%-24s pos %8.1f %8.1f %6.1f  ndc %6.2f %6.2f  px %4d %4d  depth %6.1f %s'
          % (i.get('name', '?')[:24], p[0], p[1], p[2], nx, ny, px, py, cw,
             'IN' if (-1 <= nx <= 1 and -1 <= ny <= 1) else 'out'))
print('in-frame instances:', onscreen)
