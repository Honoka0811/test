"""縦型ショート動画(1080x1920/30fps)をPillowで描画し、ffmpegでエンコードする。

usage: python3 render.py            -> out/sogo_shosha_short.mp4
       python3 render.py --still 12.3 out.png   (確認用の静止画)
"""
import json
import math
import os
import subprocess
import sys
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
TL = json.load(open(os.path.join(HERE, "build", "timeline.json")))
TOTAL = TL["total"]
LINES = TL["lines"]
CUTS = TL["scene_cuts"]
ORDER = ["intro", "p1", "p2", "p3", "p4", "p5", "outro"]

ACCENT = {
    "intro": (255, 200, 60), "p1": (255, 138, 60), "p2": (255, 84, 96),
    "p3": (64, 214, 140), "p4": (255, 214, 64), "p5": (72, 196, 255),
    "outro": (255, 200, 60),
}
WHITE = (255, 255, 255)
NAVY = (10, 16, 44)
F_DELA = os.path.join(HERE, "fonts", "DelaGothicOne.ttf")
F_BLACK = os.path.join(HERE, "fonts", "NotoSansJP-Black.ttf")
F_BOLD = os.path.join(HERE, "fonts", "NotoSansJP-Bold.ttf")


@lru_cache(None)
def font(path, size):
    return ImageFont.truetype(path, size)


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def prog(t, start, dur=0.4):
    return clamp((t - start) / dur)


# ------------------------------------------------------------------ sprites
@lru_cache(None)
def text_sprite(text, fpath, size, fill, stroke=0, stroke_fill=NAVY, shadow=0, spacing=10, align="center"):
    f = font(fpath, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    box = tmp.multiline_textbbox((0, 0), text, font=f, stroke_width=stroke, spacing=spacing, align=align)
    pad = stroke + shadow + 6
    w, h = int(box[2] - box[0] + pad * 2 + 1), int(box[3] - box[1] + pad * 2 + 1)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    o = (int(pad - box[0]), int(pad - box[1]))
    if shadow:
        d.multiline_text((o[0], o[1] + shadow), text, font=f, fill=(0, 0, 0, 150), stroke_width=stroke,
                         stroke_fill=(0, 0, 0, 150), spacing=spacing, align=align)
    d.multiline_text(o, text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill,
                     spacing=spacing, align=align)
    return img


@lru_cache(None)
def card_sprite(w, h, fill, radius=36, outline=None, width=0, shadow=True):
    m = 30
    img = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    if shadow:
        s = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).rounded_rectangle((m, m + 12, m + w, m + h + 12), radius, fill=(0, 0, 0, 120))
        img = s.filter(ImageFilter.GaussianBlur(12))
    ImageDraw.Draw(img).rounded_rectangle((m, m, m + w, m + h), radius, fill=fill, outline=outline, width=width)
    return img


def put(base, spr, cx, cy, alpha=1.0, scale=1.0):
    """spr を中心(cx,cy)に合成。alpha/scale アニメ対応。"""
    if alpha <= 0.003 or scale <= 0.01:
        return
    if abs(scale - 1.0) > 0.004:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if alpha < 0.997:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(cx - spr.width / 2), int(cy - spr.height / 2)
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(spr.width, W - x), min(spr.height, H - y)
    if ex <= sx or ey <= sy:
        return
    if (sx, sy, ex, ey) != (0, 0, spr.width, spr.height):
        spr = spr.crop((sx, sy, ex, ey))
    base.alpha_composite(spr, (x + sx, y + sy))


def pop(base, spr, cx, cy, t, start, dur=0.38, rise=40):
    """ポップイン(拡大+フェード)"""
    p = prog(t, start, dur)
    if p <= 0:
        return
    put(base, spr, cx, cy + rise * (1 - ease_out(p)), alpha=clamp(p * 2.5), scale=0.6 + 0.4 * ease_back(p))


def slide(base, spr, cx, cy, t, start, dur=0.45, dx=0, dy=60):
    p = prog(t, start, dur)
    if p <= 0:
        return
    e = ease_out(p)
    put(base, spr, cx + dx * (1 - e), cy + dy * (1 - e), alpha=clamp(p * 2.2))


def chip(text, color, size=54, fg=NAVY, padx=34, pady=18):
    return _chip(text, color, size, fg, padx, pady)


@lru_cache(None)
def _chip(text, color, size, fg, padx, pady):
    ts = text_sprite(text, F_BLACK, size, fg)
    w, h = ts.width + padx * 2, ts.height + pady * 2
    c = card_sprite(w, h, color, radius=h // 2).copy()
    c.alpha_composite(ts, ((c.width - ts.width) // 2, (c.height - ts.height) // 2 - 2))
    return c


# ------------------------------------------------------------------ background
@lru_cache(None)
def bg_base(scene):
    a = ACCENT[scene]
    top = tuple(int(NAVY[i] * 0.86 + a[i] * 0.14) for i in range(3))
    bot = (6, 9, 28)
    col = Image.new("RGB", (1, H))
    for y in range(H):
        k = y / (H - 1)
        col.putpixel((0, y), tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3)))
    return col.resize((W, H)).convert("RGBA")


@lru_cache(None)
def glow(scene, r):
    a = ACCENT[scene]
    img = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((r * 0.3, r * 0.3, r * 1.7, r * 1.7), fill=a + (70,))
    return img.filter(ImageFilter.GaussianBlur(r * 0.28))


@lru_cache(None)
def dots():
    img = Image.new("RGBA", (W, H + 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(0, H + 120, 60):
        for x in range(30, W, 60):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 255, 255, 26))
    return img


def background(scene, t):
    base = bg_base(scene).copy()
    put(base, glow(scene, 520), 180 + 90 * math.sin(t * 0.5), 420 + 70 * math.cos(t * 0.4))
    put(base, glow(scene, 620), 900 + 80 * math.cos(t * 0.33), 1420 + 90 * math.sin(t * 0.45))
    off = int((t * 24) % 60)
    base.alpha_composite(dots().crop((0, off, W, off + H)))
    return base


# ------------------------------------------------------------------ common UI
def header(base, scene, t):
    put(base, chip("総合商社のここがすごい", (255, 255, 255, 235), 38, NAVY, 30, 12), W / 2, 210)
    put(base, text_sprite("VOICEVOX:四国めたん", F_BOLD, 26, (255, 255, 255, 170)), W / 2, 272)
    # 進捗ドット (1〜5)
    idx = ORDER.index(scene)
    d = ImageDraw.Draw(base)
    for i in range(1, 6):
        cx = W / 2 + (i - 3) * 64
        on = i <= idx
        col = ACCENT[scene] if on else (255, 255, 255, 60)
        r = 13 if i == idx else 9
        d.ellipse((cx - r, 330 - r, cx + r, 330 + r), fill=col)


def subtitle(base, t):
    for e in LINES:
        if e["start"] - 0.08 <= t <= e["end"] + 0.18:
            p = prog(t, e["start"] - 0.08, 0.16)
            spr = text_sprite(e["sub"], F_BLACK, 56, WHITE, stroke=9, stroke_fill=(8, 12, 36), shadow=5, spacing=14)
            box = card_sprite(spr.width + 50, spr.height + 36, (8, 12, 36, 170), radius=32, shadow=False)
            cy = 1500 + 18 * (1 - ease_out(p))
            put(base, box, W / 2, cy, alpha=p)
            put(base, spr, W / 2, cy, alpha=p)
            return


def badge(base, scene, n, t, t0):
    a = ACCENT[scene]
    p = prog(t, t0, 0.42)
    if p <= 0:
        return
    spr = _badge(n, a)
    put(base, spr, W / 2, 520, alpha=clamp(p * 3), scale=0.4 + 0.6 * ease_back(p))


@lru_cache(None)
def _badge(n, a):
    img = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((24, 36, 276, 288), fill=(0, 0, 0, 90))
    d.ellipse((24, 24, 276, 276), fill=a, outline=WHITE, width=8)
    s1 = text_sprite("その", F_BLACK, 44, NAVY)
    s2 = text_sprite(str(n), F_DELA, 130, NAVY)
    img.alpha_composite(s1, ((300 - s1.width) // 2, 52))
    img.alpha_composite(s2, ((300 - s2.width) // 2, 92))
    return img


def headline(base, scene, text, t, t0, cy=770, size=92):
    a = ACCENT[scene]
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        spr = text_sprite(ln, F_DELA, size, WHITE, stroke=10, stroke_fill=NAVY, shadow=8)
        slide(base, spr, W / 2, cy + i * (size + 34), t, t0 + 0.12 * i, dy=70)
    p = ease_out(prog(t, t0 + 0.3, 0.5))
    if p > 0:
        y = cy + (len(lines) - 1) * (size + 34) + size * 0.5 + 44
        w = 520 * p
        ImageDraw.Draw(base).rounded_rectangle((W / 2 - w / 2, y, W / 2 + w / 2, y + 12), 6, fill=a)


def line_start(i):
    return LINES[i]["start"]


# ------------------------------------------------------------------ icons
@lru_cache(None)
def icon_ramen():
    S = 260
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, x in enumerate((80, 130, 180)):   # 湯気
        pts = [(x + 12 * math.sin(k / 3.0 + i), 96 - k * 4) for k in range(20)]
        d.line(pts, fill=(255, 255, 255, 220), width=9, joint="curve")
    d.ellipse((24, 96, 236, 156), fill=(255, 226, 150))        # スープ
    for k in range(5):                                         # 麺
        d.arc((50 + k * 26, 104, 110 + k * 26, 150), 180, 360, fill=(240, 170, 60), width=7)
    d.ellipse((150, 104, 196, 140), fill=(255, 245, 235), outline=(255, 120, 150), width=6)  # なると
    d.chord((24, 40, 236, 250), 0, 180, fill=(230, 60, 50))    # 丼
    d.rectangle((24, 136, 236, 150), fill=(230, 60, 50))
    d.rectangle((40, 160, 220, 172), fill=(255, 255, 255))
    d.rounded_rectangle((90, 238, 170, 256), 6, fill=(180, 40, 36))
    return img


@lru_cache(None)
def icon_rocket():
    S = 260
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(100, 190), (130, 258), (160, 190)], fill=(255, 170, 40))   # 炎
    d.polygon([(114, 190), (130, 232), (146, 190)], fill=(255, 240, 120))
    d.polygon([(82, 130), (40, 200), (88, 186)], fill=(230, 60, 50))       # 翼
    d.polygon([(178, 130), (220, 200), (172, 186)], fill=(230, 60, 50))
    d.rounded_rectangle((84, 60, 176, 196), 30, fill=(240, 244, 255))      # 胴体
    d.pieslice((84, 4, 176, 124), 180, 360, fill=(230, 60, 50))            # 先端
    d.ellipse((106, 86, 154, 134), fill=(72, 196, 255), outline=(40, 60, 120), width=7)
    return img.rotate(-24, resample=Image.BICUBIC)


@lru_cache(None)
def icon_globe(col):
    S = 240
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((10, 10, 230, 230), outline=col, width=10)
    d.ellipse((70, 10, 170, 230), outline=col, width=8)
    d.line((10, 120, 230, 120), fill=col, width=8)
    d.arc((24, -60, 216, 90), 20, 160, fill=col, width=8)
    d.arc((24, 150, 216, 300), 200, 340, fill=col, width=8)
    return img


# ------------------------------------------------------------------ scenes
def scene_intro(base, t):
    a = ACCENT["intro"]
    t0 = 0.15
    slide(base, text_sprite("総合商社の", F_DELA, 120, WHITE, stroke=12, shadow=10), W / 2, 640, t, t0, dy=90)
    p = prog(t, t0 + 0.35, 0.45)
    if p > 0:
        spr = text_sprite("ここがすごい！", F_DELA, 132, a, stroke=12, shadow=10)
        put(base, spr, W / 2, 820, alpha=clamp(p * 3), scale=0.5 + 0.5 * ease_back(p))
    # "5選" バッジ
    t1 = line_start(1) - 0.1
    p = prog(t, t1, 0.45)
    if p > 0:
        img = _five()
        wob = 1 + 0.03 * math.sin((t - t1) * 6)
        put(base, img, W / 2, 1130, alpha=clamp(p * 3), scale=(0.4 + 0.6 * ease_back(p)) * wob)
    slide(base, chip("60秒でわかる", (255, 255, 255, 240), 46), W / 2, 470, t, t0 + 0.6, dy=-40)


@lru_cache(None)
def _five():
    a = ACCENT["intro"]
    img = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = []
    for k in range(32):   # ギザギザ
        r = 204 if k % 2 == 0 else 176
        ang = math.pi * 2 * k / 32
        pts.append((210 + r * math.cos(ang), 210 + r * math.sin(ang)))
    d.polygon(pts, fill=(230, 60, 60))
    d.ellipse((50, 50, 370, 370), outline=WHITE, width=6)
    s = text_sprite("5", F_DELA, 210, WHITE)
    s2 = text_sprite("選", F_DELA, 96, a)
    img.alpha_composite(s, (92, 82))
    img.alpha_composite(s2, (228, 190))
    return img


def scene_p1(base, t):
    sc = "p1"
    t0 = CUTS[sc] + 0.1
    badge(base, sc, 1, t, t0)
    headline(base, sc, "扱う商品が\n幅広すぎ！", t, t0 + 0.2)
    t1 = line_start(3)
    # ラーメン → ロケット
    pop(base, icon_ramen(), 250, 1120, t, t1)
    pop(base, text_sprite("ラーメン", F_BLACK, 48, WHITE, stroke=6), 250, 1262, t, t1 + 0.05)
    p = ease_out(prog(t, t1 + 0.55, 0.5))
    if p > 0:
        d = ImageDraw.Draw(base)
        x0, x1 = 410, 410 + 260 * p
        d.line((x0, 1120, x1, 1120), fill=ACCENT[sc], width=16)
        d.polygon([(x1, 1088), (x1 + 44, 1120), (x1, 1152)], fill=ACCENT[sc])
    t2 = t1 + 1.0
    pr = prog(t, t2, 0.4)
    if pr > 0:
        bob = 10 * math.sin((t - t2) * 5)
        put(base, icon_rocket(), 830, 1120 + bob - 40 * (1 - ease_out(pr)), alpha=clamp(pr * 3),
            scale=0.6 + 0.4 * ease_back(pr))
    pop(base, text_sprite("ロケット", F_BLACK, 48, WHITE, stroke=6), 830, 1262, t, t2 + 0.05)


def scene_p2(base, t):
    sc = "p2"
    a = ACCENT[sc]
    t0 = CUTS[sc] + 0.1
    badge(base, sc, 2, t, t0)
    headline(base, sc, "実は日本独自の\nビジネスモデル", t, t0 + 0.2, size=86)
    t1 = line_start(5)
    # 日の丸カード
    p = prog(t, t0 + 0.9, 0.4)
    fade = 1 - prog(t, t1 - 0.15, 0.25)
    if p > 0 and fade > 0:
        c = _flag()
        put(base, c, W / 2, 1180, alpha=clamp(p * 3) * fade, scale=0.6 + 0.4 * ease_back(p))
    # SOGO SHOSHA タイプライター
    word = "SOGO SHOSHA"
    n = int(clamp((t - t1 - 0.2) / 0.9) * len(word) + 0.001)
    if t >= t1 - 0.05:
        slide(base, chip("英語でもそのまま通じる！", WHITE, 46), W / 2, 1060, t, t1 - 0.05, dy=40)
    if n > 0:
        full = text_sprite(word, F_DELA, 92, a, stroke=10, shadow=8)
        part = text_sprite(word[:n], F_DELA, 92, a, stroke=10, shadow=8)
        x = W / 2 - full.width / 2 + part.width / 2
        put(base, part, x, 1200)
    slide(base, text_sprite("世界でも珍しい業態", F_BLACK, 44, (255, 255, 255, 220), stroke=5), W / 2, 1310, t, t1 + 1.3, dy=30)


@lru_cache(None)
def _flag():
    c = card_sprite(420, 280, WHITE, radius=28).copy()
    d = ImageDraw.Draw(c)
    d.ellipse((30 + 210 - 84, 30 + 140 - 84, 30 + 210 + 84, 30 + 140 + 84), fill=(214, 40, 56))
    return c


def scene_p3(base, t):
    sc = "p3"
    a = ACCENT[sc]
    t0 = CUTS[sc] + 0.1
    badge(base, sc, 3, t, t0)
    headline(base, sc, "ただの貿易会社\nじゃない！", t, t0 + 0.2)
    t1, t2 = line_start(7), line_start(8)
    out = 1 - prog(t, t2 - 0.2, 0.25)
    if out > 0 and t >= t1 - 0.1:
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pop(tmp, _tile("トレーディング", "モノを動かす", (255, 255, 255)), 290, 1140, t, t1 - 0.05)
        pop(tmp, text_sprite("＋", F_BLACK, 96, a, stroke=8), W / 2, 1140, t, t1 + 0.35)
        pop(tmp, _tile("事業投資", "会社を育てる", a), 790, 1140, t, t1 + 0.7)
        pg = prog(t, t1 + 1.3, 0.4)
        if pg > 0:
            put(tmp, text_sprite("世界中で事業を経営！", F_BLACK, 58, WHITE, stroke=8, shadow=5), W / 2, 1320,
                alpha=clamp(pg * 3), scale=0.7 + 0.3 * ease_back(pg))
        if out < 1:
            tmp.putalpha(tmp.getchannel("A").point(lambda v: int(v * out)))
        base.alpha_composite(tmp)
    if t >= t2 - 0.1:
        slide(base, chip("身近なコンビニにも", WHITE, 46), W / 2, 1050, t, t2 - 0.05, dy=40)
        slide(base, _conv("ローソン", "三菱商事が出資", (60, 140, 255)), W / 2, 1175, t, t2 + 0.25, dx=-160, dy=0)
        slide(base, _conv("ファミリーマート", "伊藤忠商事グループ", (40, 190, 120)), W / 2, 1320, t, t2 + 1.2, dx=160, dy=0)


@lru_cache(None)
def _tile(title, sub, col):
    c = card_sprite(400, 230, col, radius=40).copy()
    s1 = text_sprite(title, F_BLACK, 52 if len(title) > 5 else 68, NAVY)
    s2 = text_sprite(sub, F_BOLD, 36, (40, 50, 90))
    c.alpha_composite(s1, ((c.width - s1.width) // 2, 78))
    c.alpha_composite(s2, ((c.width - s2.width) // 2, 176))
    return c


@lru_cache(None)
def _conv(name, sub, col):
    c = card_sprite(880, 130, WHITE, radius=30).copy()
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((30, 30, 60, 160), 14, fill=col)
    d.rectangle((46, 30, 60, 160), fill=col)
    s1 = text_sprite(name, F_BLACK, 50, NAVY)
    s2 = text_sprite(sub, F_BLACK, 38, col)
    c.alpha_composite(s1, (84, 30 + (130 - s1.height) // 2 - 2))
    c.alpha_composite(s2, (c.width - 30 - 34 - s2.width, 30 + (130 - s2.height) // 2 - 2))
    return c


def scene_p4(base, t):
    sc = "p4"
    a = ACCENT[sc]
    t0 = CUTS[sc] + 0.1
    badge(base, sc, 4, t, t0)
    headline(base, sc, "稼ぐ力が\nケタ違い", t, t0 + 0.2)
    t1 = line_start(10)
    slide(base, chip("2022年度 連結純利益", WHITE, 40), 320, 1050, t, t1 - 0.05, dy=40)
    # 棒グラフ(横)
    rows = [("三菱商事", 1.18, "約1.18兆円"), ("三井物産", 1.13, "約1.13兆円")]
    d = ImageDraw.Draw(base)
    for i, (name, v, lab) in enumerate(rows):
        ts = t1 + 1.0 + i * 0.75
        p = ease_out(prog(t, ts, 0.8))
        if prog(t, ts, 0.3) <= 0:
            continue
        y = 1125 + i * 118
        slide(base, text_sprite(name, F_BLACK, 46, WHITE, stroke=6), 170, y + 38, t, ts, dx=-40, dy=0)
        x0, full = 300, 520
        x1 = x0 + full * (v / 1.25) * p
        d.rounded_rectangle((x0, y, x0 + full, y + 76), 20, fill=(255, 255, 255, 30))
        d.rounded_rectangle((x0, y, max(x0 + 40, x1), y + 76), 20, fill=a)
        # 1兆円ライン
        xl = x0 + full * (1.0 / 1.25)
        d.line((xl, y - 12, xl, y + 88), fill=(255, 90, 90), width=6)
        if p > 0.9:
            put(base, text_sprite(lab, F_BLACK, 40, WHITE, stroke=6), x0 + full + 115, y + 38, alpha=clamp((p - 0.9) * 10))
    if t >= t1 + 1.0:
        xl = 300 + 520 * (1.0 / 1.25)
        slide(base, text_sprite("1兆円", F_BLACK, 34, (255, 120, 120), stroke=5), xl, 1368, t, t1 + 1.0, dy=20)
    # 1兆円突破スタンプ
    ts = line_start(10) + 3.6
    p = prog(t, ts, 0.3)
    if p > 0:
        spr = text_sprite("1兆円突破！", F_DELA, 72, (255, 80, 80), stroke=12, stroke_fill=WHITE, shadow=8).rotate(
            8, resample=Image.BICUBIC, expand=True)
        put(base, spr, 800, 1040, alpha=clamp(p * 3), scale=1.9 - 0.9 * ease_out(p))


def scene_p5(base, t):
    sc = "p5"
    a = ACCENT[sc]
    t0 = CUTS[sc] + 0.1
    badge(base, sc, 5, t, t0)
    headline(base, sc, "「投資の神様」も\n認めた！", t, t0 + 0.2, size=86)
    t1 = line_start(12)
    pop(base, _buffett(), W / 2, 1075, t, t1 - 0.05)
    names = ["三菱商事", "三井物産", "伊藤忠商事", "住友商事", "丸紅"]
    pos = [(250, 1195), (W / 2, 1195), (840, 1195), (380, 1288), (700, 1288)]
    for i, (nm, (x, y)) in enumerate(zip(names, pos)):
        pop(base, chip(nm, a, 46, NAVY, 28, 16), x, y, t, t1 + 1.3 + i * 0.16, rise=30)
    slide(base, text_sprite("2020年に5社への投資を公表", F_BOLD, 36, (255, 255, 255, 215), stroke=4), W / 2, 1364, t,
          t1 + 2.2, dy=20)


@lru_cache(None)
def _buffett():
    c = card_sprite(820, 130, WHITE, radius=32).copy()
    s1 = text_sprite("ウォーレン・バフェット", F_BLACK, 56, NAVY)
    c.alpha_composite(s1, ((c.width - s1.width) // 2, 30 + (130 - s1.height) // 2 - 2))
    return c


def scene_outro(base, t):
    sc = "outro"
    a = ACCENT[sc]
    t0 = CUTS[sc] + 0.1
    pop(base, icon_globe(a + (255,)), W / 2, 520, t, t0)
    slide(base, text_sprite("総合商社、", F_DELA, 120, WHITE, stroke=12, shadow=10), W / 2, 760, t, t0 + 0.1, dy=80)
    p = prog(t, t0 + 0.45, 0.45)
    if p > 0:
        put(base, text_sprite("おそるべし。", F_DELA, 132, a, stroke=12, shadow=10), W / 2, 930,
            alpha=clamp(p * 3), scale=0.5 + 0.5 * ease_back(p))
    t1 = line_start(14)
    p = prog(t, t1, 0.4)
    if p > 0:
        wob = 1 + 0.045 * math.sin((t - t1) * 7)
        put(base, chip("フォローしてね！", (255, 70, 90), 70, WHITE, 60, 30), W / 2, 1190,
            alpha=clamp(p * 3), scale=(0.5 + 0.5 * ease_back(p)) * wob)


SCENE_FN = {"intro": scene_intro, "p1": scene_p1, "p2": scene_p2, "p3": scene_p3,
            "p4": scene_p4, "p5": scene_p5, "outro": scene_outro}


def scene_at(t):
    cur = "intro"
    for s in ORDER:
        if t >= CUTS[s]:
            cur = s
    return cur


def render_frame(t):
    sc = scene_at(t)
    base = background(sc, t)
    header(base, sc, t)
    SCENE_FN[sc](base, t)
    subtitle(base, t)
    # シーン切替フラッシュ (アクセント色のワイプ)
    dt = t - CUTS[sc]
    if sc != "intro" and dt < 0.3:
        k = 1 - ease_out(dt / 0.3)
        ov = Image.new("RGBA", (W, H), ACCENT[sc] + (int(235 * k),))
        base.alpha_composite(ov)
    nxt = ORDER.index(sc) + 1
    if nxt < len(ORDER):
        dn = CUTS[ORDER[nxt]] - t
        if dn < 0.12:
            ov = Image.new("RGBA", (W, H), ACCENT[ORDER[nxt]] + (int(235 * (1 - dn / 0.12)),))
            base.alpha_composite(ov)
    # 終端フェードアウト
    if TOTAL - t < 0.5:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - (TOTAL - t) / 0.5))))
        base.alpha_composite(ov)
    return base.convert("RGB")


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--still":
        render_frame(float(sys.argv[2])).save(sys.argv[3])
        return
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "sogo_shosha_short.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", os.path.join(HERE, "build", "audio.wav"),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(TOTAL * FPS)
    for i in range(n):
        ff.stdin.write(render_frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"{i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
