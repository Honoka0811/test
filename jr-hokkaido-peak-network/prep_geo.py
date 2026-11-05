# japan.geojson(dataofjapan/land)から北海道と青森県北部の海岸線を抜き出し、簡略化して coast.js に書き出す
import json, math
d = json.load(open('data/japan.geojson'))
def simplify(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-12
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        dd = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L
        if dd > dmax: dmax, idx = dd, i
    if dmax > eps:
        return simplify(pts[:idx + 1], eps)[:-1] + simplify(pts[idx:], eps)
    return [pts[0], pts[-1]]
out = []
for f in d['features']:
    if f['properties']['id'] not in (1, 2): continue
    for poly in f['geometry']['coordinates']:
        ring = poly[0]
        if f['properties']['id'] == 2 and max(p[1] for p in ring) < 40.75: continue
        h = len(ring) // 2
        s = simplify(ring[:h + 1], 0.004)[:-1] + simplify(ring[h:], 0.004)
        if len(s) < 4: continue
        out.append({'pref': f['properties']['id'], 'pts': [[round(x, 3), round(y, 3)] for x, y in s]})
open('coast.js', 'w').write('window.COAST=' + json.dumps(out, separators=(',', ':')) + ';\n')
print(len(out), sum(len(o['pts']) for o in out))
