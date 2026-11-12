# -*- coding: utf-8 -*-
"""Natural Earth (10m) から動画用の地図データ data/geo.js を作る。
使い方: python3 build_map.py <ne_10m_admin_0_countries.shp> <ne_10m_admin_1_states_provinces.shp>
国境・海岸線は現在のもの。1930年代の領域は次のように近似する:
  内地 = 日本 + 千島列島 / 朝鮮 = 韓国 + 北朝鮮 / 台湾 / 樺太 = サハリン島の北緯50度以南
  満洲 = 黒竜江・吉林・遼寧の3省 + 内モンゴル自治区の東部(東経116度以東)※概略
"""
import sys, json, os
import geopandas as gpd
from shapely.geometry import box, mapping
from shapely.ops import unary_union

c = gpd.read_file(sys.argv[1]); p = gpd.read_file(sys.argv[2])
BBOX = box(98, 5, 165, 62)
def country(a3): return unary_union(c[c.ADM0_A3 == a3].geometry.values)
def prov(names): return unary_union(p[(p.adm0_a3 == 'CHN') & p.name.isin(names)].geometry.values)

rus = country('RUS')
karafuto = rus.intersection(box(141.5, 45.8, 145.0, 50.0))
kuril = rus.intersection(box(145.3, 43.3, 156.6, 50.9))
regions = {
    'naichi': unary_union([country('JPN'), kuril]),
    'chosen': unary_union([country('KOR'), country('PRK')]),
    'taiwan': country('TWN'),
    'karafuto': karafuto,
    'manshu': unary_union([prov(['Heilongjiang', 'Jilin', 'Liaoning']),
                           prov(['Inner Mongol']).intersection(box(116, 41.3, 127, 54))]),
}
empire = unary_union(list(regions.values()))
others = []
for _, r in c.iterrows():
    g = r.geometry.intersection(BBOX)
    if g.is_empty: continue
    g = g.difference(empire.buffer(1e-6))
    if not g.is_empty: others.append(g)

def rings(g, tol, min_area):
    g = g.simplify(tol, preserve_topology=True)
    polys = [g] if g.geom_type == 'Polygon' else [x for x in getattr(g, 'geoms', []) if x.geom_type == 'Polygon']
    out = []
    for poly in polys:
        if poly.area < min_area: continue
        out.append([[round(x, 3), round(y, 3)] for x, y in poly.exterior.coords])
    return out

geo = {'others': [r for g in others for r in rings(g, 0.02, 0.004)],
       'regions': {k: rings(v, 0.006, 0.0006) for k, v in regions.items()}}
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'geo.js')
with open(dst, 'w') as f:
    f.write('window.GEO=' + json.dumps(geo, separators=(',', ':')) + ';')
print('wrote', dst, os.path.getsize(dst) // 1024, 'KB', {k: len(v) for k, v in geo['regions'].items()}, len(geo['others']))
