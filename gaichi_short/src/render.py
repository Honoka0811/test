import math, os, sys, subprocess, random
from functools import lru_cache
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from timeline import build, HERE

W, H, FPS = 1080, 1920, 30
FD = os.path.join(HERE, "..", "fonts", "package")
F_DELA = os.path.join(FD, "400Regular", "DelaGothicOne_400Regular.ttf")
F_BLACK = os.path.join(FD, "900Black", "NotoSansJP_900Black.ttf")
F_BOLD = os.path.join(FD, "700Bold", "NotoSansJP_700Bold.ttf")
SCENES, TOTAL = build()
S = {s["key"]: s for s in SCENES}

REG = {"朝鮮": (255, 77, 109), "台湾": (46, 196, 182), "関東州": (255, 183, 3),
       "樺太": (142, 202, 230), "南洋": (6, 214, 160), "北方領土": (160, 196, 255)}
# rank, city, ruby, region, now, pop(万), shares (naichi, local, foreign), local label, extra
# rank: (city, ruby, region, now, pop万, shares(内地, local, other), local label, extra, other label, breakdown source)
RANKS = {
    10: ("台南", "たいなん", "台湾", "現在：台南（タイナン）", 14, (12.3, 85.6, 2.2), "本島人", None, "外国人ほか", "内訳：台湾常住戸口統計 昭和15年末"),
    9: ("高雄", "たかお", "台湾", "現在：高雄（カオシュン）", 15, (19.8, 79.0, 1.3), "本島人", None, "外国人ほか", "内訳：台湾常住戸口統計 昭和15年末"),
    8: ("仁川", "じんせん", "朝鮮", "現在：仁川（インチョン）", 17, (10.0, 89.0, 1.0), "朝鮮人", None, "外国人", "内訳：朝鮮総督府統計年報 昭和15年（1940年末）"),
    7: ("大邱", "たいきゅう", "朝鮮", "現在：大邱（テグ）", 18, (11.1, 88.7, 0.1), "朝鮮人", None, "外国人", "内訳：朝鮮総督府統計年報 昭和15年（1940年末）"),
    6: ("清津", "せいしん", "朝鮮", "現在：清津（チョンジン）", 20, (14.4, 84.5, 1.1), "朝鮮人", None, "外国人", "内訳：朝鮮総督府統計年報 昭和15年（1940年末）"),
    5: ("釜山", "ふざん", "朝鮮", "現在：釜山（プサン）", 25, (22.6, 77.3, 0.1), "朝鮮人", "住民の2割が内地人", "外国人", "内訳：朝鮮総督府統計年報 昭和15年（1940年末）"),
    4: ("平壌", "へいじょう", "朝鮮", "現在：平壌（ピョンヤン）", 29, (9.7, 89.5, 0.8), "朝鮮人", None, "外国人", "内訳：朝鮮総督府統計年報 昭和15年（1940年末）"),
    3: ("台北", "たいほく", "台湾", "現在：台北（タイペイ）", 33, (28.4, 67.7, 3.9), "本島人", "住民の3割近くが内地人", "外国人ほか", "内訳：台湾常住戸口統計 昭和15年末"),
    2: ("大連", "だいれん", "関東州", "現在：大連（ダーリエン）", 66, (27.7, 71.3, 1.0), "中国人", "住民の7割が中国人", "朝鮮人ほか", "内訳：関東局統計書 第35（1940年末）"),
    1: ("京城", "けいじょう", "朝鮮", "現在：ソウル", 94, (16.2, 83.3, 0.5), "朝鮮人", "横浜・神戸に迫る大都市", "外国人", "内訳：朝鮮総督府統計年報 昭和15年（1940年末）"),
}
SRC_TOTAL = "人口：1940年国勢調査（内閣統計局『列国国勢要覧』昭和18年版）"
SUBS = {
    "hook": "戦前、日本が治めた「外地」。\nいちばん人口が多かった都市は？",
    "title": "外地の都市 人口ランキング TOP10！",
    "r10": "第10位 台湾・台南 約14万人", "r9": "第9位 高雄 約15万人",
    "r8": "第8位 朝鮮・仁川 約17万人", "r7": "第7位 大邱 約18万人",
    "r6": "第6位 北の港町・清津 約20万人", "r5": "第5位 釜山 約25万人\n住民の2割が内地人",
    "r4": "第4位 平壌 約29万人", "r3": "第3位！台北 約33万人\n住民の3割近くが内地人！",
    "r2": "第2位！関東州・大連 約66万人\n住民の7割は中国人",
    "tease": "そして、栄えある第1位は……",
    "r1": "京城！今のソウル！約94万人\n横浜や神戸に迫る大都市！",
    "extra": "ここからは おまけ",
    "kara": "樺太庁が置かれた豊原は約4万人\n樺太全体では住民の9割以上が内地人",
    "nanyo": "南洋群島の人口は約13万人、うち移住者約7.7万人\n沖縄出身者が最多。コロール・ガラパンは1万人超とされる※",
    "hoppo": "北方領土は外地ではなく北海道の一部\n1945年、四島で約1万7千人が漁業を中心に暮らす",
    "outro": "あなたの予想は当たった？\nコメントで教えてください！",
}
# (region, title, ruby, sub, stat, notes, source, weak-evidence note)
EXTRAS = {
    "kara": ("樺太", "豊原", "とよはら", "現在：ユジノサハリンスク", "約3.9万人",
             ["樺太庁の所在地（1940年末）", "樺太全体の内地人は96.6%（1935年）", "樺太全体で約41.5万人（1940年）"],
             "出典：樺太庁統計書（二次資料経由）／1935・1940年国勢調査",
             "※豊原の人口は二次資料による値。1941年末には恵須取町が上回る"),
    "nanyo": ("南洋", "コロール／ガラパン", None, "パラオ／サイパン", "全体 約12.9万人",
              ["うち移住者 約7.7万人・島民 約5.2万人", "移住者は沖縄出身者が最多", "コロールは南洋庁の所在地"],
              "出典：南洋庁『南洋庁統計年鑑』昭和14年（1939年末）",
              "※コロール・ガラパンの町の人口は資料により差があり、確定値ではない"),
    "hoppo": ("北方領土", "国後・択捉・色丹・歯舞", None, "※外地ではなく北海道の一部", "四島で17,291人",
              ["1945年8月15日時点の人口", "主な産業は漁業", "泊・紗那・斜古丹など"],
              "出典：北方領土問題対策協会「北方領土の位置・面積・人口」", None),
}

@lru_cache(maxsize=64)
def font(path, size): return ImageFont.truetype(path, size)

def ease_out(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3
def ease_back(x):
    x = max(0, min(1, x)); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def clamp(x, a=0, b=1): return max(a, min(b, x))

@lru_cache(maxsize=256)
def text_img(txt, path, size, fill=(255, 255, 255), stroke=0, sfill=(0, 0, 0), glow=None):
    f = font(path, size)
    l, t, r, b = f.getbbox(txt, stroke_width=stroke)
    pad = 40 if glow else 6
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((pad - l, pad - t), txt, font=f, fill=glow + (255,), stroke_width=stroke + 6, stroke_fill=glow + (255,))
        g = g.filter(ImageFilter.GaussianBlur(18))
        im.alpha_composite(g)
    d.text((pad - l, pad - t), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)
    return im

def paste_c(canvas, im, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01: return
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        im = im.copy(); a = im.getchannel("A").point(lambda v: int(v * alpha)); im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def paste_l(canvas, im, x, cy, alpha=1.0):
    paste_c(canvas, im, x + im.width / 2, cy, 1.0, alpha)

# ---------- background ----------
_BG = None
def bg_base():
    global _BG
    if _BG is None:
        g = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(g)
        for y in range(H):
            k = y / H
            d.line([(0, y), (W, y)], fill=(int(10 + 18 * k), int(14 + 6 * k), int(32 + 26 * k)))
        grid = Image.new("RGBA", (W + 120, H + 120), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grid)
        for x in range(0, W + 120, 120): gd.line([(x, 0), (x, H + 120)], fill=(120, 150, 220, 22), width=2)
        for y in range(0, H + 120, 120): gd.line([(0, y), (W + 120, y)], fill=(120, 150, 220, 22), width=2)
        vig = Image.new("L", (W, H), 0)
        ImageDraw.Draw(vig).ellipse([-300, -200, W + 300, H + 200], fill=255)
        vig = vig.filter(ImageFilter.GaussianBlur(220))
        _BG = (g.convert("RGBA"), grid, vig)
    return _BG

random.seed(3)
PARTS = [(random.random() * W, random.random() * H, random.uniform(2, 6), random.uniform(15, 60)) for _ in range(70)]

def background(t, accent=(90, 120, 255), dark=0.0):
    g, grid, vig = bg_base()
    c = g.copy()
    off = int(t * 30) % 120
    c.alpha_composite(grid.crop((off, off, off + W, off + H)))
    # accent glow
    glow = Image.new("RGBA", (W, H), accent + (0,))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([W / 2 - 700, 500, W / 2 + 700, 1500], fill=70)
    m = m.filter(ImageFilter.GaussianBlur(160)) if False else m
    glow.putalpha(_blurred_mask())
    tint = Image.new("RGBA", (W, H), accent + (255,)); tint.putalpha(_blurred_mask())
    c.alpha_composite(tint)
    d = ImageDraw.Draw(c)
    for (x, y, r, sp) in PARTS:
        yy = (y - t * sp) % H
        xx = x + math.sin(t * 0.7 + y) * 20
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(200, 220, 255, 60))
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    inv = vig.point(lambda v: int((255 - v) * 0.85))
    black.putalpha(inv); c.alpha_composite(black)
    if dark > 0:
        c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dark))))
    return c

_MASK = None
def _blurred_mask():
    global _MASK
    if _MASK is None:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([W / 2 - 650, 450, W / 2 + 650, 1450], fill=60)
        _MASK = m.filter(ImageFilter.GaussianBlur(170))
    return _MASK

# ---------- common UI ----------
def header(c, t_in):
    a = ease_out(t_in / 0.4)
    paste_c(c, text_img("戦前の外地", F_BLACK, 46, (255, 210, 90)), W / 2, 170, 1, a)
    paste_c(c, text_img("都市人口ランキング", F_DELA, 78, (255, 255, 255), 4, (20, 20, 40)), W / 2, 250, 1, a)

def credit(c):
    paste_l(c, text_img("VOICEVOX:青山龍星", F_BOLD, 30, (230, 230, 240), 3, (0, 0, 0)), 40, 80, 0.9)
    im = text_img("※数値は1940年前後の統計", F_BOLD, 28, (200, 200, 215), 3, (0, 0, 0))
    paste_c(c, im, W - 40 - im.width / 2, 80, 1, 0.9)

def subtitle(c, key, lt):
    txt = SUBS.get(key)
    if not txt: return
    a = ease_out(lt / 0.15)
    lines = txt.split("\n")
    y0 = 1525
    for i, ln in enumerate(lines):
        im = text_img(ln, F_BLACK, 58, (255, 255, 255), 8, (10, 10, 20))
        s = 1.0 if im.width < W - 80 else (W - 80) / im.width
        paste_c(c, im, W / 2, y0 + i * 84, s * (0.92 + 0.08 * a), a)

def progress(c, rank, lt):
    # dots for ranks 10..1 at left
    for i, r in enumerate(range(10, 0, -1)):
        y = 520 + i * 78
        done = r > rank or (r == rank and lt > 0.15)
        col = (255, 210, 90, 255) if done else (255, 255, 255, 60)
        d = ImageDraw.Draw(c)
        rad = 15 if r == rank else 10
        d.ellipse([40 - rad, y - rad, 40 + rad, y + rad], fill=col)
        if r == rank:
            paste_c(c, text_img(str(r), F_DELA, 22, (20, 20, 30)), 40, y)

def stacked_bar(c, shares, local_label, accent, p, y=1180):
    x0, bw, bh = 110, 860, 54
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([x0 - 6, y - 6, x0 + bw + 6, y + bh + 6], 16, fill=(0, 0, 0, 140))
    cols = [accent + (255,), (110, 125, 160, 255), (196, 150, 70, 255)]
    labels = ["内地人", local_label, "外国人"]
    x = x0; tot = bw * ease_out(p)
    for sh, col in zip(shares, cols):
        w = bw * sh / 100
        w2 = max(0, min(w, x0 + tot - x))
        if w2 > 0: d.rectangle([x, y, x + w2, y + bh], fill=col)
        x += w
    # legend
    lx = x0; a = clamp((p - 0.6) / 0.4)
    for sh, col, lb in zip(shares, cols, labels):
        if sh < 1 and lb != "外国人": continue
        d.rounded_rectangle([lx, y + 84, lx + 30, y + 114], 6, fill=col[:3] + (int(255 * a),))
        im = text_img(f"{lb} {sh}%" if sh >= 1 else f"{lb} 1%未満", F_BOLD, 36, (235, 235, 245), 3, (0, 0, 0))
        paste_l(c, im, lx + 38, y + 99, a)
        lx += im.width + 70

def rank_scene(c, r, lt, dur):
    city, ruby, reg, now, pop, shares, ll, extra = RANKS[r][:8]
    acc = REG[reg] if r != 1 else (255, 200, 40)
    header(c, 10)
    progress(c, r, lt)
    # rank number slam
    sc = 2.4 - 1.4 * ease_back(lt / 0.28)
    num = text_img(f"{r}", F_DELA, 260, acc, 10, (15, 15, 30), glow=acc)
    i_ = text_img("位", F_DELA, 120, (255, 255, 255), 8, (15, 15, 30))
    a = clamp(lt / 0.1)
    paste_c(c, num, W / 2 - 50, 470, sc, a)
    paste_c(c, i_, W / 2 + num.width * 0.5 * sc - 50 + 40, 520, sc, a)
    # region pill
    p2 = ease_out((lt - 0.2) / 0.3)
    if p2 > 0:
        tag = text_img(reg, F_BLACK, 44, (20, 20, 30))
        d = ImageDraw.Draw(c)
        wpx = tag.width + 50; x = W / 2 - wpx / 2; y = 640
        d.rounded_rectangle([x, y, x + wpx, y + 72], 36, fill=acc + (int(255 * p2),))
        paste_c(c, tag, W / 2, y + 36, 1, p2)
    # city name slide
    p3 = ease_back((lt - 0.25) / 0.4)
    if lt > 0.25:
        cx = W / 2 + (1 - p3) * 700
        paste_c(c, text_img(ruby, F_BOLD, 46, (255, 230, 160), 4, (10, 10, 20)), cx, 770, 1, clamp(p3))
        paste_c(c, text_img(city, F_DELA, 190, (255, 255, 255), 10, (10, 10, 25), glow=acc), cx, 890, 1, clamp(p3))
        paste_c(c, text_img(now, F_BOLD, 42, (210, 220, 240), 4, (10, 10, 20)), cx, 1010, 1, clamp(p3))
    # count up
    p4 = ease_out((lt - 0.45) / 0.6)
    if lt > 0.45:
        val = int(round(pop * p4))
        im1 = text_img("約", F_BLACK, 70, (255, 255, 255), 6, (10, 10, 20))
        im2 = text_img(f"{val}", F_DELA, 130, (255, 225, 110), 8, (10, 10, 20), glow=(255, 160, 0))
        im3 = text_img("万人", F_BLACK, 70, (255, 255, 255), 6, (10, 10, 20))
        tw = im1.width + im2.width + im3.width - 60
        x = W / 2 - tw / 2; yy = 1095
        pop_s = 1 + 0.15 * math.exp(-max(0, lt - 1.05) * 8) * (lt > 1.05)
        paste_c(c, im1, x + im1.width / 2, yy + 20)
        paste_c(c, im2, x + im1.width - 30 + im2.width / 2, yy, pop_s)
        paste_c(c, im3, x + im1.width + im2.width - 60 + im3.width / 2, yy + 20)
    stacked_bar(c, shares, ll, acc, (lt - 0.9) / 0.7, 1210)
    if extra and lt > 1.6:
        pe = ease_back((lt - 1.6) / 0.35)
        d = ImageDraw.Draw(c)
        im = text_img(extra, F_BLACK, 48, (20, 20, 30))
        wpx = im.width + 60
        layer = Image.new("RGBA", (wpx + 20, 110), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle([10, 10, wpx + 10, 100], 20, fill=(255, 225, 110, 255))
        layer.alpha_composite(im, (int((wpx + 20 - im.width) / 2), int((110 - im.height) / 2)))
        layer = layer.rotate(-4, expand=True, resample=Image.BICUBIC)
        paste_c(c, layer, W / 2 + 150, 1385, pe)

def rays(c, t, col=(255, 200, 60), alpha=60):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = W / 2, 880
    for i in range(16):
        a0 = t * 0.4 + i * 2 * math.pi / 16
        a1 = a0 + math.pi / 32
        R = 2000
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=col + (alpha,))
    c.alpha_composite(layer)

random.seed(11)
CONF = [(random.uniform(0, W), random.uniform(-600, 0), random.uniform(250, 600), random.uniform(-80, 80),
         random.choice([(255, 210, 90), (255, 77, 109), (46, 196, 182), (255, 255, 255), (160, 196, 255)]),
         random.uniform(0, 6.28)) for _ in range(140)]

def confetti(c, lt):
    d = ImageDraw.Draw(c)
    for (x, y, vy, vx, col, ph) in CONF:
        yy = y + vy * lt; xx = x + vx * lt + 30 * math.sin(lt * 3 + ph)
        if -50 < yy < H + 50:
            s = 9 * abs(math.sin(lt * 5 + ph)) + 3
            d.rectangle([xx - 9, yy - s, xx + 9, yy + s], fill=col + (230,))

def hook_scene(c, lt, dur):
    a = ease_out(lt / 0.4)
    paste_c(c, text_img("戦前の日本", F_BLACK, 70, (255, 210, 90), 6, (0, 0, 0)), W / 2, 420, 1, a)
    p = ease_back((lt - 0.4) / 0.4)
    if lt > 0.4:
        paste_c(c, text_img("外地 最大の都市は", F_DELA, 96, (255, 255, 255), 8, (10, 10, 25)), W / 2, 560, p)
    # cycling candidate names
    if lt > 1.4:
        names = ["京城？", "大連？", "台北？", "平壌？", "釜山？", "高雄？"]
        k = int((lt - 1.4) / 0.32) % len(names)
        ph = ((lt - 1.4) / 0.32) % 1
        s = 1.25 - 0.25 * ease_out(ph / 0.4)
        paste_c(c, text_img(names[k], F_DELA, 200, (255, 255, 255), 10, (10, 10, 25), glow=(255, 77, 109)), W / 2, 880, s, 1)
    qs = 1 + 0.08 * math.sin(lt * 8)
    paste_c(c, text_img("?", F_DELA, 300, (255, 77, 109), 10, (10, 10, 25)), W - 170, 1180, qs, 0.6 * a)
    paste_c(c, text_img("?", F_DELA, 220, (46, 196, 182), 10, (10, 10, 25)), 160, 1150, 2 - qs, 0.5 * a)

def title_scene(c, lt, dur):
    rays(c, lt, (255, 200, 60), 28)
    p = ease_back(lt / 0.35)
    paste_c(c, text_img("戦前の外地", F_BLACK, 80, (255, 210, 90), 6, (0, 0, 0)), W / 2, 560, p)
    paste_c(c, text_img("都市人口", F_DELA, 170, (255, 255, 255), 10, (10, 10, 25)), W / 2, 740, 3 - 2 * ease_back(lt / 0.3))
    paste_c(c, text_img("ランキング", F_DELA, 170, (255, 255, 255), 10, (10, 10, 25)), W / 2, 920, 3 - 2 * ease_back((lt - 0.12) / 0.3), clamp((lt - 0.1) / 0.1))
    if lt > 0.5:
        s = ease_back((lt - 0.5) / 0.35) * (1 + 0.05 * math.sin(lt * 10))
        paste_c(c, text_img("TOP10", F_DELA, 200, (255, 77, 109), 10, (255, 255, 255), glow=(255, 77, 109)), W / 2, 1120, s)
    if lt > 1.0:
        paste_c(c, text_img("朝鮮・台湾・関東州", F_BLACK, 54, (220, 230, 255), 5, (0, 0, 0)), W / 2, 1290, 1, ease_out((lt - 1) / 0.4))

def tease_scene(c, lt, dur):
    header(c, 10)
    progress(c, 1, 0)
    z = 1 + 0.4 * (lt / dur) ** 2
    paste_c(c, text_img("第1位は…", F_DELA, 140, (255, 255, 255), 8, (10, 10, 25)), W / 2, 620, ease_back(lt / 0.3))
    sh = (lt / dur) ** 2 * 18
    q = text_img("?", F_DELA, 420, (255, 210, 90), 12, (10, 10, 25), glow=(255, 160, 0))
    paste_c(c, q, W / 2 + random.uniform(-sh, sh), 980 + random.uniform(-sh, sh), z)

def extra_card(c, key, lt, dur):
    reg, title, ruby, sub, stat, notes = EXTRAS[key][:6]
    acc = REG[reg]
    paste_c(c, text_img("おまけ", F_DELA, 64, (255, 210, 90), 5, (10, 10, 25)), W / 2, 220)
    p = ease_back(lt / 0.4)
    d = ImageDraw.Draw(c)
    x0 = 70 + (1 - p) * 900; y0 = 330; x1 = x0 + W - 140; y1 = 1330
    d.rounded_rectangle([x0, y0, x1, y1], 40, fill=(15, 20, 45, 230), outline=acc + (255,), width=6)
    cx = (x0 + x1) / 2
    tag = text_img(reg, F_BLACK, 50, (20, 20, 30))
    d.rounded_rectangle([cx - tag.width / 2 - 30, y0 + 50, cx + tag.width / 2 + 30, y0 + 130], 40, fill=acc + (255,))
    paste_c(c, tag, cx, y0 + 90)
    if ruby: paste_c(c, text_img(ruby, F_BOLD, 44, (255, 230, 160), 3, (0, 0, 0)), cx, y0 + 200)
    t_im = text_img(title, F_DELA, 130 if len(title) <= 4 else 84, (255, 255, 255), 8, (10, 10, 25), glow=acc)
    s = min(1, (W - 220) / t_im.width)
    paste_c(c, t_im, cx, y0 + 310, s)
    paste_c(c, text_img(sub, F_BOLD, 42, (210, 220, 240), 3, (0, 0, 0)), cx, y0 + 430)
    ps = ease_back((lt - 0.4) / 0.35)
    if lt > 0.4:
        paste_c(c, text_img(stat, F_DELA, 110, (255, 225, 110), 8, (10, 10, 25), glow=(255, 160, 0)), cx, y0 + 570, ps)
    for i, n in enumerate(notes):
        pn = ease_out((lt - 0.9 - i * 0.25) / 0.3)
        if pn > 0:
            im = text_img("● " + n, F_BOLD, 46, (235, 235, 245), 3, (0, 0, 0))
            paste_l(c, im, x0 + 90 - (1 - pn) * 60, y0 + 720 + i * 80, pn)

def outro_scene(c, lt, dur):
    rays(c, lt, (255, 200, 60), 20)
    paste_c(c, text_img("TOP3", F_DELA, 90, (255, 210, 90), 6, (10, 10, 25)), W / 2, 330, ease_back(lt / 0.3))
    rows = [("1", "京城", "約93万人", (255, 210, 90)), ("2", "大連", "約55万人", (220, 225, 235)), ("3", "台北", "約35万人", (230, 160, 100))]
    d = ImageDraw.Draw(c)
    for i, (r, n, p_, col) in enumerate(rows):
        pr = ease_back((lt - 0.2 - i * 0.15) / 0.35)
        if pr <= 0: continue
        y = 480 + i * 170; x = 120 + (1 - pr) * -900
        d.rounded_rectangle([x, y, x + 840, y + 140], 30, fill=(15, 20, 45, 230), outline=col + (255,), width=5)
        paste_c(c, text_img(r, F_DELA, 90, col, 6, (10, 10, 25)), x + 90, y + 70)
        paste_l(c, text_img(n, F_DELA, 90, (255, 255, 255), 6, (10, 10, 25)), x + 170, y + 70)
        im = text_img(p_, F_BLACK, 56, (255, 225, 110), 5, (10, 10, 25))
        paste_c(c, im, x + 840 - 40 - im.width / 2, y + 70)
    if lt > 1.0:
        s = ease_back((lt - 1.0) / 0.35) * (1 + 0.04 * math.sin(lt * 7))
        paste_c(c, text_img("予想は当たった？", F_DELA, 100, (255, 255, 255), 8, (10, 10, 25), glow=(255, 77, 109)), W / 2, 1060, s)
        paste_c(c, text_img("コメントで教えて！", F_BLACK, 66, (255, 210, 90), 6, (0, 0, 0)), W / 2, 1200, s)
    if lt > 2.0:
        a = ease_out((lt - 2) / 0.4)
        paste_c(c, text_img("ナレーション　VOICEVOX:青山龍星", F_BOLD, 40, (235, 235, 245), 4, (0, 0, 0)), W / 2, 1310, 1, a)

def frame(fi):
    t = fi / FPS
    sc = next((s for s in SCENES if s["start"] <= t < s["end"]), SCENES[-1])
    key = sc["key"]; lt = t - sc["start"]; dur = sc["end"] - sc["start"]
    accent = (90, 120, 255); dark = 0.0
    if key.startswith("r") and key[1:].isdigit():
        accent = REG[RANKS[int(key[1:])][2]]
    elif key in EXTRAS: accent = REG[EXTRAS[key][0]]
    elif key == "tease": dark = 0.35 + 0.3 * lt / dur; accent = (255, 160, 0)
    elif key == "hook": accent = (255, 77, 109)
    elif key in ("title", "outro"): accent = (255, 180, 60)
    c = background(t, accent, dark)
    if key == "r1":
        rays(c, t, (255, 200, 60), 45)
    if key == "hook": hook_scene(c, lt, dur)
    elif key == "title": title_scene(c, lt, dur)
    elif key == "tease": tease_scene(c, lt, dur)
    elif key == "extra":
        p = ease_back(lt / 0.35)
        paste_c(c, text_img("おまけ", F_DELA, 220, (255, 210, 90), 10, (10, 10, 25), glow=(255, 160, 0)), W / 2, 760, p)
        paste_c(c, text_img("樺太・南洋・北方領土", F_BLACK, 64, (255, 255, 255), 6, (0, 0, 0)), W / 2, 960, 1, ease_out((lt - 0.3) / 0.3))
    elif key in EXTRAS: extra_card(c, key, lt, dur)
    elif key == "outro": outro_scene(c, lt, dur)
    else: rank_scene(c, int(key[1:]), lt, dur)
    if key == "r1": confetti(c, lt)
    vlt = t - sc["vstart"]
    subtitle(c, key, max(0, vlt) if vlt > -0.1 else -1) if vlt > -0.1 else None
    credit(c)
    # flash + shake on slams
    flash = 0; shake = 0
    if (key.startswith("r") and key[1:].isdigit()) or key in ("title",):
        flash = max(0, 1 - lt / 0.25) * (0.9 if key in ("r1", "title") else 0.45)
        shake = max(0, 1 - lt / 0.3) * (34 if key in ("r1", "title") else 16)
    if key in ("extra", "kara", "nanyo", "hoppo", "outro"):
        flash = max(0, 1 - lt / 0.15) * 0.25
    if flash > 0:
        c.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * flash))))
    out = c.convert("RGB")
    if shake > 0:
        rr = random.Random(fi)
        dx, dy = int(rr.uniform(-shake, shake)), int(rr.uniform(-shake, shake))
        z = 1.04
        big = out.resize((int(W * z), int(H * z)), Image.BILINEAR)
        ox = (big.width - W) // 2 + dx; oy = (big.height - H) // 2 + dy
        out = big.crop((ox, oy, ox + W, oy + H))
    return out.tobytes()

def main():
    n = int(TOTAL * FPS)
    only = sys.argv[1:]  # preview frames
    if only:
        for s in only:
            fi = int(float(s) * FPS)
            Image.frombytes("RGB", (W, H), frame(fi)).save(os.path.join(HERE, f"prev_{s}.png"))
        return
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", os.path.join(HERE, "mix.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           os.path.join(HERE, "out.mp4")], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, range(n), chunksize=8)):
            ff.stdin.write(b)
            if i % 300 == 0: print(i, "/", n, flush=True)
    ff.stdin.close(); ff.wait()
    print("done")

if __name__ == "__main__":
    main()
