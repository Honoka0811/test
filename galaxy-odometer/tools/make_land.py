# -*- coding: utf-8 -*-
"""Natural Earth(パブリックドメイン)の陸地ポリゴンを正距円筒図法のマスク画像にして data/land.js に埋め込む。
使い方: python3 tools/make_land.py ne_50m_land.geojson
入手元: https://github.com/nvkelso/natural-earth-vector (geojson/ne_50m_land.geojson)
"""
import base64, io, json, os, sys
from PIL import Image, ImageDraw

src = sys.argv[1]
W, H, SS = 2048, 1024, 3
img = Image.new('L', (W * SS, H * SS), 0)
d = ImageDraw.Draw(img)
gj = json.load(open(src, encoding='utf-8'))


def ring_xy(ring):
    return [((lon + 180) / 360 * W * SS, (90 - lat) / 180 * H * SS) for lon, lat in ring]


for f in gj['features']:
    g = f['geometry']
    polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    for poly in polys:
        d.polygon(ring_xy(poly[0]), fill=255)
        for hole in poly[1:]:
            d.polygon(ring_xy(hole), fill=0)
img = img.resize((W, H), Image.LANCZOS)
buf = io.BytesIO()
img.save(buf, 'PNG', optimize=True)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'land.js')
with open(out, 'w') as f:
    f.write('// Natural Earth 1:50m land (public domain) を正距円筒図法でラスタライズした陸地マスク\n')
    f.write('window.LAND_PNG = "data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode() + '";\n')
print('wrote', out, len(buf.getvalue()), 'bytes png')
img.save('/tmp/claude-0/-home-user-test/4f3d6d7f-ab07-5f16-907e-d9dfb10d7b85/scratchpad/land_preview.png')
