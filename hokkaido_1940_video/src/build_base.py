import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from common import *
geo = json.load(open(sys.argv[1]))
def polys(fid):
    for f in geo['features']:
        if f['properties']['id'] == fid:
            g = f['geometry']; cs = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
            for poly in cs:
                yield [[(world(x, y)[0] * K, world(x, y)[1] * K) for x, y in ring] for ring in poly]
print(BASE_W, BASE_H)
# sea gradient
yy = np.linspace(0, 1, BASE_H)[:, None]
top = np.array([10, 24, 44]); bot = np.array([14, 40, 66])
sea = (top + (bot - top) * yy)[:, None, :].repeat(BASE_W, 1)[:, :, :] if False else None
sea = np.empty((BASE_H, BASE_W, 3), np.float32)
for c in range(3): sea[:, :, c] = top[c] + (bot[c] - top[c]) * yy
rng = np.random.default_rng(1)
sea += rng.normal(0, 1.6, (BASE_H, BASE_W, 1))
img = Image.fromarray(np.clip(sea, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)
# graticule
for lon in range(136, 149):
    x = world(lon, 0)[0] * K; d.line([(x, 0), (x, BASE_H)], fill=(32, 58, 88), width=2)
for lat in range(36, 49):
    y = world(0, lat)[1] * K; d.line([(0, y), (BASE_W, y)], fill=(32, 58, 88), width=2)
def mask_of(ids):
    m = Image.new('L', (BASE_W, BASE_H), 0); md = ImageDraw.Draw(m)
    for fid in ids:
        for poly in polys(fid):
            md.polygon(poly[0], fill=255)
            for hole in poly[1:]: md.polygon(hole, fill=0)
    return m
hk = mask_of([1]); hon = mask_of([2, 3, 4, 5, 6])
# honshu (dim)
img.paste(Image.new('RGB', img.size, (38, 56, 78)), (0, 0), hon)
edge = hon.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
img.paste(Image.new('RGB', img.size, (70, 94, 120)), (0, 0), edge)
# hokkaido glow + shadow
glow = hk.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(28))
img = Image.composite(Image.new('RGB', img.size, (80, 200, 210)), img, glow.point(lambda v: int(v * 0.45)))
sh = hk.filter(ImageFilter.GaussianBlur(14)); sh = Image.fromarray(np.roll(np.array(sh), (14, 10), (0, 1)))
img = Image.composite(Image.new('RGB', img.size, (4, 10, 20)), img, sh.point(lambda v: int(v * 0.6)))
# land with paper texture
land = np.empty((BASE_H, BASE_W, 3), np.float32); land[:] = (241, 230, 204)
tex = Image.fromarray(rng.normal(128, 40, (BASE_H // 8, BASE_W // 8)).clip(0, 255).astype(np.uint8)).resize((BASE_W, BASE_H), Image.BICUBIC)
land += (np.array(tex, np.float32)[:, :, None] - 128) * 0.10
land += rng.normal(0, 3, (BASE_H, BASE_W, 1))
# inner shading toward coast
inner = np.array(hk.filter(ImageFilter.GaussianBlur(40)), np.float32) / 255
land *= (0.86 + 0.14 * inner)[:, :, None]
img.paste(Image.fromarray(land.clip(0, 255).astype(np.uint8)), (0, 0), hk)
coast = hk.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1))
img = Image.composite(Image.new('RGB', img.size, (150, 116, 72)), img, coast)
img.save('base.png'); hk.save('hk_mask.png')
print('saved')
