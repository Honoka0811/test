# -*- coding: utf-8 -*-
"""world-atlas の land-50m.json (TopoJSON) を欧州〜中東の範囲に切り出し、陸地ポリゴンを JS ファイル(window.LAND_DATA)にする。
使い方: python3 tools/make_land.py land-50m.json assets/land_europe.js"""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
topo = json.load(open(src))
sx, sy = topo['transform']['scale']; tx, ty = topo['transform']['translate']
arcs = []
for arc in topo['arcs']:
    x = y = 0; pts = []
    for dx, dy in arc:
        x += dx; y += dy
        pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)
def ring(idx):
    out = []
    for i in idx:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        out.extend(a if not out else a[1:])
    return out
LON0, LON1, LAT0, LAT1 = -25, 60, 25, 72
polys = []
for g in topo['objects']['land']['geometries']:
    for poly in g['arcs']:
        r = ring(poly[0])
        if not any(LON0 <= x <= LON1 and LAT0 <= y <= LAT1 for x, y in r):
            continue
        if len(r) < 8: continue
        polys.append([[round(x, 2), round(y, 2)] for x, y in r])
open(dst, 'w').write('window.LAND_DATA=' + json.dumps(polys, separators=(',', ':')) + ';\n')
print(len(polys), 'polygons', sum(len(p) for p in polys), 'points')
