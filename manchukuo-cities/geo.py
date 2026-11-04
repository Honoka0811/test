# -*- coding: utf-8 -*-
"""Natural Earth(パブリックドメイン)の GeoJSON から、動画用の地図データ geo.js を作る。
使い方: python3 geo.py <Natural Earth geojson のディレクトリ>
必要なファイル: ne_50m_admin_0_countries / ne_50m_coastline / ne_50m_rivers_lake_centerlines / ne_50m_lakes (.geojson)
満洲国の国境は、現在の中国国境のうち東北部分 + 南西側(熱河省・興安省の西端)を手で近似した線で構成する。
"""
import json, os, sys, math

SRC = sys.argv[1] if len(sys.argv) > 1 else '.'
HERE = os.path.dirname(os.path.abspath(__file__))
BBOX = (100.0, 28.0, 150.0, 58.0)  # lon0, lat0, lon1, lat1

def load(name):
    with open(os.path.join(SRC, name + '.geojson'), encoding='utf-8') as f:
        return json.load(f)['features']

def clip_ring(ring, box=BBOX):
    """矩形で多角形をクリップ(Sutherland–Hodgman)"""
    x0, y0, x1, y1 = box
    edges = [(lambda p: p[0] >= x0, lambda a, b: _ix(a, b, x0, 0)),
             (lambda p: p[0] <= x1, lambda a, b: _ix(a, b, x1, 0)),
             (lambda p: p[1] >= y0, lambda a, b: _ix(a, b, y0, 1)),
             (lambda p: p[1] <= y1, lambda a, b: _ix(a, b, y1, 1))]
    out = ring
    for inside, inter in edges:
        if not out: break
        inp, out = out, []
        prev = inp[-1]
        for cur in inp:
            if inside(cur):
                if not inside(prev): out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
            prev = cur
    return out

def _ix(a, b, v, axis):
    t = (v - a[axis]) / (b[axis] - a[axis])
    p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
    p[axis] = v
    return p

def in_box(pts, box=BBOX):
    return any(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in pts)

def simplify(pts, eps=0.03):
    """Douglas–Peucker"""
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + b[0] * a[1] - b[1] * a[0]) / n
        if d > dmax: dmax, idx = d, i
    if dmax > eps:
        return simplify(pts[:idx + 1], eps)[:-1] + simplify(pts[idx:], eps)
    return [a, b]

def rnd(pts): return [[round(x, 2), round(y, 2)] for x, y in pts]

def polys(geom):
    if geom['type'] == 'Polygon': return [geom['coordinates']]
    if geom['type'] == 'MultiPolygon': return geom['coordinates']
    return []

def lines(geom):
    if geom['type'] == 'LineString': return [geom['coordinates']]
    if geom['type'] == 'MultiLineString': return geom['coordinates']
    return []

# ---------- 陸地(国ごと) ----------
land = []
china_ring = None
for f in load('ne_50m_admin_0_countries'):
    iso = f['properties'].get('ADM0_A3')
    for poly in polys(f['geometry']):
        ring = [p[:2] for p in poly[0]]
        if iso == 'CHN' and (china_ring is None or len(ring) > len(china_ring)):
            china_ring = ring
        if not in_box(ring): continue
        c = clip_ring(ring)
        if len(c) < 3: continue
        land.append({'iso': iso, 'pts': rnd(simplify(c + [c[0]], 0.02))})

# ---------- 満洲国の国境(近似) ----------
# 中国の外周のうち、北東側の区間(モンゴル国境上の点 → 山海関)を取り出す
def nearest(ring, p):
    return min(range(len(ring)), key=lambda i: (ring[i][0] - p[0]) ** 2 + (ring[i][1] - p[1]) ** 2)
ring = china_ring[:-1]
i_start = nearest(ring, (119.9, 46.7))  # ハルハ河付近(モンゴル国境)
i_end = nearest(ring, (119.8, 40.0))    # 山海関(渤海沿岸)
n = len(ring)
arc_a = [ring[(i_start + k) % n] for k in range((i_end - i_start) % n + 1)]
arc_b = [ring[(i_end + k) % n] for k in range((i_start - i_end) % n + 1)][::-1]
# 北東端(ウスリー川付近 lon>133)を通る方を採用
arc = arc_a if max(p[0] for p in arc_a) > 133 else arc_b
if arc[0] != ring[i_start]: arc = arc[::-1]
# 南西側の境界(熱河省・興安西省の西端を近似)。山海関 → 長城沿い → 多倫の東 → 北上してハルハ河へ
sw = [(119.8, 40.0), (119.2, 40.25), (118.6, 40.35), (117.9, 40.55), (117.3, 40.6), (116.7, 40.9),
      (116.3, 41.3), (116.4, 41.9), (116.9, 42.5), (117.6, 43.2), (118.3, 43.9), (118.9, 44.7),
      (119.4, 45.4), (119.7, 46.1), (119.9, 46.7)]
manchukuo = arc + [list(p) for p in sw[1:]]
manchukuo = rnd(simplify(manchukuo, 0.02))

# ---------- 海岸線・河川・湖 ----------
coast = []
for f in load('ne_50m_coastline'):
    for ln in lines(f['geometry']):
        if in_box(ln): coast.append(rnd(simplify([p[:2] for p in ln], 0.02)))

RIVERS = {'Amur': '黒龍江', 'Songhua': '松花江', 'Ussuri': 'ウスリー川', 'Yalu': '鴨緑江', 'Liao': '遼河',
          'Nen': '嫩江', 'Argun': 'アルグン川', 'Tumen': '図們江', 'Mudan': '牡丹江'}
rivers = []
for f in load('ne_50m_rivers_lake_centerlines'):
    name = f['properties'].get('name') or ''
    for ln in lines(f['geometry']):
        if in_box(ln, (110, 37, 140, 54)):
            rivers.append({'name': name, 'pts': rnd(simplify([p[:2] for p in ln], 0.02))})

lakes = []
for f in load('ne_50m_lakes'):
    for poly in polys(f['geometry']):
        ring = [p[:2] for p in poly[0]]
        if in_box(ring, (110, 37, 140, 54)):
            lakes.append(rnd(simplify(ring, 0.02)))

out = os.path.join(HERE, 'geo.js')
with open(out, 'w', encoding='utf-8') as f:
    f.write('// 自動生成: python3 geo.py  (Natural Earth 1:50m, パブリックドメイン)\n')
    f.write('window.GEO = ' + json.dumps({'land': land, 'manchukuo': manchukuo, 'coast': coast,
                                         'rivers': rivers, 'lakes': lakes}, separators=(',', ':')) + ';\n')
print('wrote', out, os.path.getsize(out) // 1024, 'KB',
      f'land={len(land)} coast={len(coast)} rivers={len(rivers)} lakes={len(lakes)} manchukuo={len(manchukuo)}pts')
