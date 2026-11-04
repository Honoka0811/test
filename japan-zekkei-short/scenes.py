# -*- coding: utf-8 -*-
"""写真が無い場合に使うイメージイラスト（手続き的に生成）"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1350, 2400  # 1080x1920 の 1.25 倍（ズーム演出用の余白）


def grad(top, bottom, w=W, h=H, curve=1.0):
    t = (np.linspace(0, 1, h) ** curve)[:, None, None]
    a = np.array(top, float)[None, None, :]
    b = np.array(bottom, float)[None, None, :]
    arr = a * (1 - t) + b * t
    return Image.fromarray(np.repeat(arr, w, axis=1).astype(np.uint8), "RGB")


def ridge(base_y, amp, seed, rough=6, w=W):
    rnd = random.Random(seed)
    phases = [(rnd.uniform(0, 6.28), rnd.uniform(0.6, 1.0) / (i + 1)) for i in range(rough)]
    pts = []
    for x in range(0, w + 10, 10):
        y = base_y
        for i, (p, a) in enumerate(phases):
            y -= amp * a * math.sin(x / w * math.pi * (i + 1) * 1.7 + p)
        pts.append((x, y))
    return pts


def layer(img, pts, color, blur=0, bottom=H):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.polygon(pts + [(W, bottom), (0, bottom)], fill=color)
    if blur:
        lay = lay.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(lay)


def glow(img, xy, r, color, strength=200):
    lay = Image.new("RGBA", img.size, color + (0,))
    d = ImageDraw.Draw(lay)
    x, y = xy
    d.ellipse((x - r, y - r, x + r, y + r), fill=color + (strength,))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(r * 0.6)))


def finish(img, seed=0):
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    rng = np.random.default_rng(seed)
    rgb += rng.normal(0, 3.5, rgb.shape)
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.35 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2
    rgb *= v[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def s_bridge():
    img = grad((70, 150, 235), (200, 235, 250), curve=0.8).convert("RGBA")
    sea = grad((40, 200, 190), (10, 110, 150), h=H - 1000).convert("RGBA")
    img.alpha_composite(sea, (0, 1000))
    layer(img, ridge(1000, 25, 3), (60, 110, 90, 255), bottom=1012)
    d = ImageDraw.Draw(img)
    for i in range(40):  # 波のきらめき
        y = 1050 + i * 34
        d.line([(0, y), (W, y + 6)], fill=(255, 255, 255, 25), width=2)
    # 橋（手前から奥へ伸びる）
    d.polygon([(W * 0.15, H), (W * 0.85, H), (W * 0.53, 1010), (W * 0.49, 1010)], fill=(225, 225, 220, 255))
    d.polygon([(W * 0.3, H), (W * 0.7, H), (W * 0.52, 1010), (W * 0.50, 1010)], fill=(110, 110, 115, 255))
    for k in range(25):
        t = (k / 25) ** 2
        y = 1010 + (H - 1010) * t
        d.line([(W * 0.51 - 4, y), (W * 0.51 + 4, y)], fill=(255, 255, 255, 255), width=max(2, int(12 * t)))
    for i in range(4):  # 雲
        glow(img, (200 + i * 330, 300 + (i % 2) * 150), 120, (255, 255, 255), 150)
    return finish(img, 1)


def s_gorge():
    img = grad((140, 190, 170), (20, 70, 60)).convert("RGBA")
    glow(img, (W // 2, 300), 400, (230, 255, 220), 160)
    layer(img, [(0, 0), (W * 0.32, 0), (W * 0.38, 900), (W * 0.30, 1700), (W * 0.36, H), (0, H)][:-2]
          + [(W * 0.36, H)], (40, 60, 45, 255))
    d = ImageDraw.Draw(img)
    d.polygon([(0, 0), (W * 0.33, 0), (W * 0.40, 900), (W * 0.32, 1700), (W * 0.38, H), (0, H)], fill=(45, 70, 50, 255))
    d.polygon([(W, 0), (W * 0.68, 0), (W * 0.62, 900), (W * 0.70, 1700), (W * 0.64, H), (W, H)], fill=(40, 62, 48, 255))
    # 苔・緑
    rnd = random.Random(9)
    for _ in range(500):
        x = rnd.choice([rnd.uniform(0, W * 0.38), rnd.uniform(W * 0.63, W)])
        y = rnd.uniform(0, H)
        r = rnd.uniform(8, 40)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(rnd.randint(40, 100), rnd.randint(110, 170), 60, 160))
    # 滝
    fall = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fall)
    for i in range(60):
        x = W * 0.36 + rnd.uniform(0, 30)
        fd.line([(x, 500), (x + rnd.uniform(-10, 10), 1750)], fill=(255, 255, 255, 120), width=rnd.randint(3, 9))
    img.alpha_composite(fall.filter(ImageFilter.GaussianBlur(3)))
    water = grad((40, 140, 120), (10, 60, 60), h=H - 1700).convert("RGBA")
    img.alpha_composite(water, (0, 1700))
    glow(img, (int(W * 0.37), 1720), 160, (255, 255, 255), 200)
    # ボート
    d = ImageDraw.Draw(img)
    d.polygon([(W * 0.48, 2050), (W * 0.62, 2050), (W * 0.60, 2090), (W * 0.50, 2090)], fill=(200, 60, 50, 255))
    return finish(img, 2)


def s_bluepond():
    img = grad((150, 200, 230), (230, 240, 245)).convert("RGBA")
    layer(img, ridge(800, 120, 4), (110, 140, 160, 255), blur=4)
    layer(img, ridge(950, 40, 5), (40, 90, 60, 255))
    pond = grad((120, 215, 235), (20, 140, 190), h=H - 1050).convert("RGBA")
    img.alpha_composite(pond, (0, 1050))
    d = ImageDraw.Draw(img)
    rnd = random.Random(7)
    for _ in range(26):  # 立ち枯れの木
        x = rnd.uniform(0, W)
        y0 = rnd.uniform(1150, 2200)
        h = rnd.uniform(250, 700) * (y0 / 1500)
        wdt = max(3, int(h / 50))
        d.line([(x, y0), (x + rnd.uniform(-15, 15), y0 - h)], fill=(200, 195, 185, 255), width=wdt)
        for b in range(4):
            by = y0 - h * rnd.uniform(0.4, 0.9)
            d.line([(x, by), (x + rnd.uniform(-60, 60), by - rnd.uniform(30, 90))], fill=(190, 185, 175, 255), width=max(2, wdt // 2))
        # 映り込み
        d.line([(x, y0), (x, y0 + h * 0.5)], fill=(150, 200, 210, 120), width=wdt)
    return finish(img, 3)


def s_cloudcastle():
    img = grad((70, 100, 170), (255, 195, 150), curve=1.2).convert("RGBA")
    glow(img, (W // 2, 1050), 260, (255, 220, 160), 230)
    layer(img, ridge(1050, 90, 11), (70, 70, 110, 255), blur=3)
    rnd = random.Random(5)
    for i in range(140):  # 雲海
        x, y = rnd.uniform(-100, W + 100), rnd.uniform(1150, 1700)
        glow(img, (int(x), int(y)), rnd.randint(90, 200), (255, 245, 240), 255)
    # 石垣
    d = ImageDraw.Draw(img)
    d.polygon([(0, 1650), (W * 0.2, 1600), (W * 0.45, 1640), (W * 0.7, 1580), (W, 1620), (W, H), (0, H)], fill=(60, 50, 50, 255))
    for k in range(5):
        y = 1660 + k * 120
        for j in range(12):
            x = j * 120 + (k % 2) * 60
            d.rectangle((x, y, x + 110, y + 110), outline=(90, 75, 70, 255), width=4)
    layer(img, [(0, 1900), (W, 1950)], (40, 35, 35, 255))
    return finish(img, 4)


def s_forest():
    img = grad((70, 120, 80), (20, 50, 30)).convert("RGBA")
    rnd = random.Random(12)
    for i in range(14):  # 光の筋
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        x = rnd.uniform(0, W)
        ImageDraw.Draw(lay).polygon([(x, 0), (x + 60, 0), (x + 400, H), (x + 200, H)], fill=(240, 255, 200, 40))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(img)
    for i in range(18):  # 木の幹
        x = rnd.uniform(-50, W)
        w = rnd.uniform(30, 110)
        c = rnd.randint(40, 70)
        d.rectangle((x, 0, x + w, H), fill=(c, c + 20, c - 10, 255))
    # 縄文杉風の巨木
    d.polygon([(W * 0.3, H), (W * 0.36, 600), (W * 0.42, 0), (W * 0.62, 0), (W * 0.64, 700), (W * 0.75, H)], fill=(80, 70, 50, 255))
    for _ in range(1600):  # 苔
        x, y = rnd.uniform(0, W), rnd.uniform(1300, H)
        r = rnd.uniform(10, 45)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(rnd.randint(60, 130), rnd.randint(140, 200), rnd.randint(40, 80), 200))
    return finish(img, 5)


def s_beach():
    img = grad((40, 130, 230), (180, 225, 250), curve=0.7).convert("RGBA")
    for i in range(5):
        glow(img, (150 + i * 280, 250 + (i % 2) * 180), 110, (255, 255, 255), 170)
    sea = np.zeros((1300, W, 3), float)
    t = np.linspace(0, 1, 1300)[:, None]
    deep, mid, shallow = np.array([20, 80, 170]), np.array([20, 190, 210]), np.array([150, 240, 230])
    col = np.where(t < 0.5, deep * (1 - t * 2) + mid * t * 2, mid * (2 - t * 2) + shallow * (t * 2 - 1))
    sea[:] = col[:, None, :] if col.ndim == 2 else col
    img.alpha_composite(Image.fromarray(sea.astype(np.uint8)).convert("RGBA"), (0, 900))
    d = ImageDraw.Draw(img)
    d.polygon([(0, 1850), (W * 0.4, 1950), (W, 1880), (W, H), (0, H)], fill=(250, 245, 230, 255))
    for i in range(3):
        d.line([(0, 1840 + i * 15), (W * 0.4, 1940 + i * 15), (W, 1870 + i * 15)], fill=(255, 255, 255, 180), width=6, joint="curve")
    return finish(img, 6)


def s_snowvillage():
    img = grad((10, 15, 50), (60, 70, 120)).convert("RGBA")
    layer(img, ridge(1000, 150, 21), (30, 40, 70, 255), blur=2)
    layer(img, ridge(1150, 60, 22), (200, 210, 230, 255))
    d = ImageDraw.Draw(img)
    rnd = random.Random(3)
    houses = sorted([(rnd.uniform(-100, W), rnd.uniform(1250, 2100)) for _ in range(11)], key=lambda p: p[1])
    for x, y in houses:
        s = y / 1500
        w, h = 260 * s, 300 * s
        d.rectangle((x, y, x + w, y + h * 0.5), fill=(70, 45, 30, 255))
        for k in range(2):
            wx = x + w * (0.2 + 0.45 * k)
            d.rectangle((wx, y + h * 0.12, wx + w * 0.2, y + h * 0.35), fill=(255, 200, 100, 255))
        glow(img, (int(x + w / 2), int(y + h * 0.25)), int(90 * s), (255, 190, 90), 150)
        d = ImageDraw.Draw(img)
        d.polygon([(x - w * 0.12, y + 4), (x + w / 2, y - h), (x + w * 1.12, y + 4)], fill=(235, 240, 250, 255))
        d.polygon([(x + w * 0.35, y - h * 0.3), (x + w * 0.5, y - h * 0.55), (x + w * 0.65, y - h * 0.3)], fill=(255, 210, 120, 255))
    for _ in range(500):  # 降雪
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.uniform(1.5, 5)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 200))
    return finish(img, 7)


def s_alps():
    img = grad((90, 150, 220), (210, 230, 245)).convert("RGBA")
    pts = ridge(900, 330, 31, rough=8)
    layer(img, pts, (110, 120, 140, 255))
    # 冠雪
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).polygon([(x, y) for x, y in pts] + [(W, 820), (0, 820)], fill=(250, 250, 255, 230))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).polygon(pts + [(W, H), (0, H)], fill=255)
    snow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    snow.paste(lay, (0, 0), mask)
    img.alpha_composite(snow)
    layer(img, ridge(1250, 60, 32), (40, 90, 60, 255))
    rnd = random.Random(8)
    d = ImageDraw.Draw(img)
    for _ in range(120):  # 針葉樹
        x = rnd.uniform(0, W)
        y = rnd.uniform(1200, 1500)
        h = rnd.uniform(60, 160)
        d.polygon([(x, y - h), (x - h * 0.25, y), (x + h * 0.25, y)], fill=(30, rnd.randint(70, 100), 50, 255))
    river = grad((150, 210, 220), (60, 150, 170), h=H - 1450).convert("RGBA")
    img.alpha_composite(river, (0, 1450))
    d = ImageDraw.Draw(img)
    d.polygon([(0, 1450), (W * 0.25, 1450), (0, 2100)], fill=(40, 90, 60, 255))
    d.polygon([(W, 1450), (W * 0.75, 1450), (W, 2200)], fill=(40, 90, 60, 255))
    for i in range(30):
        y = 1500 + i * 30
        d.line([(W * 0.3, y), (W * 0.7, y + 4)], fill=(255, 255, 255, 40), width=2)
    return finish(img, 8)


def s_snowwall():
    img = grad((20, 90, 210), (130, 190, 245)).convert("RGBA")
    d = ImageDraw.Draw(img)
    vx, vy = W * 0.5, 900
    d.polygon([(0, 300), (vx - 40, vy), (vx - 40, vy + 60), (W * 0.18, H), (0, H)], fill=(235, 240, 248, 255))
    d.polygon([(W, 250), (vx + 40, vy), (vx + 40, vy + 60), (W * 0.82, H), (W, H)], fill=(220, 228, 240, 255))
    d.polygon([(W * 0.18, H), (vx - 40, vy + 60), (vx + 40, vy + 60), (W * 0.82, H)], fill=(80, 80, 85, 255))
    for k in range(1, 30):  # 雪の層
        t = k / 30
        d.line([(0, 300 + t * (H - 300)), (vx - 40, vy + t * 60)], fill=(200, 210, 225, 255), width=3)
        d.line([(W, 250 + t * (H - 250)), (vx + 40, vy + t * 60)], fill=(190, 200, 220, 255), width=3)
    # 人のシルエット（スケール感）
    for x, y, s in [(W * 0.45, 1700, 1.0), (W * 0.55, 1450, 0.6)]:
        d.ellipse((x - 18 * s, y - 150 * s, x + 18 * s, y - 114 * s), fill=(40, 40, 50, 255))
        d.rectangle((x - 22 * s, y - 112 * s, x + 22 * s, y), fill=(200, 60, 60, 255))
    return finish(img, 9)


def s_fuji():
    img = grad((80, 140, 225), (240, 200, 210), curve=1.2).convert("RGBA")
    d = ImageDraw.Draw(img)
    fx, fy = W * 0.62, 650
    d.polygon([(fx, fy), (fx - 900, 1500), (fx + 900, 1500)], fill=(70, 90, 140, 255))
    d.polygon([(fx - 60, fy), (fx - 290, fy + 280), (fx - 180, fy + 240), (fx - 80, fy + 300), (fx + 40, fy + 230),
               (fx + 160, fy + 300), (fx + 290, fy + 280), (fx + 60, fy)], fill=(250, 250, 255, 255))
    glow(img, (int(W * 0.3), 1500), 300, (255, 255, 255), 120)
    # 五重塔
    d = ImageDraw.Draw(img)
    px, base = W * 0.28, 1900
    d.rectangle((px - 8, base - 950, px + 8, base - 800), fill=(60, 30, 25, 255))
    for i in range(5):
        y = base - i * 160
        w = 230 - i * 22
        d.rectangle((px - w * 0.55, y - 120, px + w * 0.55, y), fill=(190, 50, 40, 255))
        d.polygon([(px - w, y - 110), (px + w, y - 110), (px + w * 0.7, y - 160), (px - w * 0.7, y - 160)], fill=(50, 40, 40, 255))
    # 桜
    rnd = random.Random(4)
    for _ in range(900):
        x = rnd.choice([rnd.uniform(-100, W * 0.15), rnd.uniform(W * 0.45, W + 100)]) if rnd.random() < 0.6 else rnd.uniform(0, W)
        y = rnd.uniform(1850, H)
        r = rnd.uniform(25, 70)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, rnd.randint(170, 215), rnd.randint(200, 230), 210))
    for _ in range(150):  # 舞う花びら
        x, y = rnd.uniform(0, W), rnd.uniform(0, 1900)
        d.ellipse((x, y, x + 12, y + 8), fill=(255, 200, 220, 200))
    return finish(img, 10)


SCENES = {
    "bridge": s_bridge, "gorge": s_gorge, "bluepond": s_bluepond, "cloudcastle": s_cloudcastle,
    "forest": s_forest, "beach": s_beach, "snowvillage": s_snowvillage, "alps": s_alps,
    "snowwall": s_snowwall, "fuji": s_fuji,
}
