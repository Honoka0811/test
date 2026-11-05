# -*- coding: utf-8 -*-
"""dataofjapan/land の japan.geojson を簡略化し、描画用の map_data.js を書き出す。
使い方: python3 make_map.py japan.geojson
(正距円筒図法 + cos(36°) で経度を補正。沖縄・小笠原など遠隔離島と小さな島は省略)"""
import sys, json, math
src = json.load(open(sys.argv[1], encoding='utf-8'))
K = math.cos(math.radians(36))
def proj(p): return (p[0] * K, -p[1])

def rdp(pts, eps):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-12
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * (pts[i][0] - a[0]) - dx * (pts[i][1] - a[1])) / L
        if d > dmax: dmax, idx = d, i
    if dmax > eps:
        return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [a, b]

def area(r): return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2

out = {}
for f in src['features']:
    name = f['properties']['nam_ja']
    if name == '沖縄県': continue
    g = f['geometry']
    polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    rings = []
    for poly in polys:
        ring = poly[0]
        lat = sum(p[1] for p in ring) / len(ring)
        if lat < 30: continue
        r = [proj(p) for p in ring]
        if area(r) < 0.004: continue
        # 閉じたリングは最遠点で2分割してから簡略化
        far = max(range(len(r)), key=lambda i: (r[i][0] - r[0][0]) ** 2 + (r[i][1] - r[0][1]) ** 2)
        r = rdp(r[:far + 1], 0.012)[:-1] + rdp(r[far:], 0.012)
        if len(r) >= 4: rings.append(r)
    out[name] = rings
xs = [p[0] for rs in out.values() for r in rs for p in r]; ys = [p[1] for rs in out.values() for r in rs for p in r]
x0, y0 = min(xs), min(ys); s = max(max(xs) - x0, max(ys) - y0)
res = {}
for n, rs in out.items():
    res[n] = [[[round((p[0] - x0) / s, 4), round((p[1] - y0) / s, 4)] for p in r] for r in rs]
w, h = (max(xs) - x0) / s, (max(ys) - y0) / s
with open('map_data.js', 'w', encoding='utf-8') as f:
    f.write('// 生成: make_map.py (元データ: dataofjapan/land japan.geojson)\n')
    f.write(f'window.MAP_W={w:.4f};window.MAP_H={h:.4f};\nwindow.MAP=' + json.dumps(res, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(len(res), 'prefs', sum(len(r) for rs in res.values() for r in rs), 'pts', f'w={w:.3f} h={h:.3f}')
