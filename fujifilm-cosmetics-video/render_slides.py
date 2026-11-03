# -*- coding: utf-8 -*-
"""シーンごとの 1920x1080 スライド画像を Pillow で描く。
使い方: python3 render_slides.py <font_dir> <out_dir>
"""
import sys, os, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scenario import SCENES

W, H = 1920, 1080
FONT_DIR, OUT_DIR = sys.argv[1], sys.argv[2]
os.makedirs(OUT_DIR, exist_ok=True)

def font(weight, size):
    name = {"R": "NotoSansCJKjp-Regular.otf", "B": "NotoSansCJKjp-Bold.otf", "K": "NotoSansCJKjp-Black.otf"}[weight]
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

# palette
NAVY = (18, 22, 38); NAVY2 = (34, 40, 68); RED = (214, 32, 58); RED2 = (255, 92, 110)
CREAM = (248, 244, 238); GOLD = (236, 190, 96); MINT = (120, 220, 200); WHITE = (255, 255, 255)
GREY = (170, 176, 196)

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def gradient_bg(c1, c2, diag=True):
    img = Image.new("RGB", (W, H), c1)
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=lerp(c1, c2, y / H))
    if diag:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.polygon([(W * 0.62, 0), (W, 0), (W, H), (W * 0.52, H)], fill=(255, 255, 255, 10))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    return img

def rounded(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def text_fit(d, xy, s, fnt, fill, maxw):
    """単純な折り返し描画。戻り値は描いた高さ"""
    x, y = xy; line = ""; lines = []
    for ch in s:
        if d.textlength(line + ch, font=fnt) > maxw and line:
            lines.append(line); line = ch
        else:
            line += ch
    lines.append(line)
    lh = fnt.size * 1.35
    for i, ln in enumerate(lines):
        d.text((x, y + i * lh), ln, font=fnt, fill=fill)
    return len(lines) * lh

# ---------------- illustrations (drawn into a 760x560 RGBA card) ----------------
CW, CH = 780, 600

def card_base(bg=(28, 32, 54)):
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rounded(d, (0, 0, CW - 1, CH - 1), 34, fill=bg + (255,))
    return img, d

def glow(img, color, center, radius, alpha=120):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.ellipse([center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius], fill=color + (alpha,))
    ov = ov.filter(ImageFilter.GaussianBlur(radius / 2.2))
    return Image.alpha_composite(img, ov)

def bottle(d, x, y, w, h, body, cap=(40, 40, 48), label=None, fnt=None, label_color=WHITE, shape="tall"):
    """化粧品ボトルのシルエット"""
    if shape == "jar":
        rounded(d, (x, y + h * 0.18, x + w, y + h), 28, fill=body)
        rounded(d, (x + w * 0.04, y, x + w * 0.96, y + h * 0.26), 12, fill=cap)
    elif shape == "tube":
        d.polygon([(x + w * 0.2, y + h * 0.12), (x + w * 0.8, y + h * 0.12), (x + w * 0.95, y + h), (x + w * 0.05, y + h)], fill=body)
        rounded(d, (x + w * 0.33, y, x + w * 0.67, y + h * 0.14), 6, fill=cap)
    else:
        rounded(d, (x, y + h * 0.22, x + w, y + h), 26, fill=body)
        rounded(d, (x + w * 0.3, y, x + w * 0.7, y + h * 0.26), 8, fill=cap)
    # highlight
    d.rounded_rectangle((x + w * 0.1, y + h * 0.3, x + w * 0.2, y + h * 0.92), radius=8, fill=tuple(min(255, c + 40) for c in body))
    if label:
        lw = w * 0.74; lx = x + (w - lw) / 2; ly = y + h * 0.48
        rounded(d, (lx, ly, lx + lw, ly + h * 0.3), 10, fill=(250, 248, 244))
        if fnt:
            # center label text
            lines = label.split("\n")
            ty = ly + h * 0.15 - len(lines) * fnt.size * 0.65
            for ln in lines:
                tw = d.textlength(ln, font=fnt)
                d.text((lx + (lw - tw) / 2, ty), ln, font=fnt, fill=label_color); ty += fnt.size * 1.25

def film_strip(d, x, y, w, h, color=(60, 62, 80), hole=(14, 16, 28), frames=4, fill_frames=None):
    rounded(d, (x, y, x + w, y + h), 10, fill=color)
    hw, hh = w / (frames * 6), h * 0.09
    for i in range(frames * 3):
        hx = x + 14 + i * (w - 28) / (frames * 3)
        rounded(d, (hx, y + 10, hx + hw, y + 10 + hh), 3, fill=hole)
        rounded(d, (hx, y + h - 10 - hh, hx + hw, y + h - 10), 3, fill=hole)
    fw = (w - 40) / frames
    for i in range(frames):
        fx = x + 20 + i * fw
        c = fill_frames[i] if fill_frames else (90, 110, 150)
        rounded(d, (fx + 6, y + h * 0.2, fx + fw - 6, y + h * 0.8), 6, fill=c)

def illust_intro():
    img, d = card_base((24, 20, 36)); img = glow(img, RED, (560, 420), 230, 110); d = ImageDraw.Draw(img)
    film_strip(d, 50, 90, 460, 150, fill_frames=[(120, 140, 190), (160, 120, 170), (210, 110, 120), (230, 150, 110)])
    # arrow
    d.polygon([(420, 300), (520, 300), (520, 280), (580, 320), (520, 360), (520, 340), (420, 340)], fill=GOLD)
    bottle(d, 560, 250, 120, 300, RED, cap=(60, 20, 28), label="ASTA\nLIFT", fnt=font("K", 24), label_color=RED)
    bottle(d, 420, 380, 100, 190, (235, 236, 240), cap=(200, 70, 90), shape="jar")
    d.text((50, 300), "写真フィルム", font=font("B", 40), fill=CREAM)
    d.text((50, 360), "↓", font=font("B", 40), fill=GOLD)
    d.text((50, 420), "スキンケア", font=font("B", 40), fill=CREAM)
    return img

def illust_film_crash():
    img, d = card_base((26, 30, 48))
    # axis
    ox, oy = 90, 500; d.line([(ox, 80), (ox, oy), (720, oy)], fill=GREY, width=4)
    pts = [(ox, 130), (200, 125), (290, 150), (380, 230), (470, 360), (560, 440), (680, 480)]
    d.line(pts, fill=RED2, width=10, joint="curve")
    for p in pts: d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], fill=CREAM)
    d.text((110, 70), "写真フィルム需要", font=font("B", 34), fill=CREAM)
    d.text((330, 300), "2000年代\n急減", font=font("K", 46), fill=RED2)
    d.text((ox, 520), "2000", font=font("R", 26), fill=GREY); d.text((630, 520), "2010", font=font("R", 26), fill=GREY)
    # camera icon
    rounded(d, (540, 110, 700, 220), 14, fill=(60, 66, 90)); d.ellipse([590, 130, 650, 190], fill=(30, 34, 50), outline=MINT, width=5)
    d.text((548, 226), "デジタル化", font=font("B", 26), fill=MINT)
    return img

def illust_org():
    img, d = card_base((26, 30, 48))
    def box(x, y, w, h, c, s, fnt, tc=WHITE):
        rounded(d, (x, y, x + w, y + h), 16, fill=c)
        lines = s.split("\n"); ty = y + h / 2 - len(lines) * fnt.size * 0.7
        for ln in lines:
            tw = d.textlength(ln, font=fnt); d.text((x + (w - tw) / 2, ty), ln, font=fnt, fill=tc); ty += fnt.size * 1.3
    box(190, 40, 400, 80, (70, 76, 110), "富士フイルムホールディングス", font("B", 28))
    d.line([(390, 120), (390, 160)], fill=GREY, width=4)
    d.line([(130, 160), (650, 160)], fill=GREY, width=4)
    for x, s, c in [(40, "イメージング", (60, 66, 92)), (300, "ヘルスケア", RED), (560, "ビジネス\nイノベーション", (60, 66, 92))]:
        d.line([(x + 90, 160), (x + 90, 190)], fill=GREY, width=4)
        box(x, 190, 180, 90, c, s, font("B", 24))
    d.line([(390, 280), (390, 320)], fill=RED2, width=4)
    for x, s, c in [(30, "医療機器", (70, 76, 110)), (230, "バイオCDMO", (70, 76, 110)), (430, "ライフサイエンス\n化粧品・サプリ", RED), ]:
        d.line([(x + 90, 320), (x + 90, 340)], fill=GREY, width=3)
        box(x, 340, 180 if x != 430 else 310, 100, c, s, font("B", 22))
    d.line([(390, 320), (585, 320)], fill=GREY, width=3); d.line([(120, 320), (390, 320)], fill=GREY, width=3)
    box(60, 480, 660, 90, (40, 44, 70), "富士フイルムヘルスケアラボラトリー（事業会社）", font("B", 26), CREAM)
    return img

def illust_collagen():
    img, d = card_base((30, 26, 40)); img = glow(img, GOLD, (390, 300), 240, 70); d = ImageDraw.Draw(img)
    # triple helix
    for k, col in enumerate([(240, 200, 120), (230, 150, 110), (250, 230, 190)]):
        pts = []
        for i in range(0, 640, 4):
            x = 70 + i; y = 300 + 95 * math.sin(i / 60 + k * 2.1)
            pts.append((x, y))
        d.line(pts, fill=col, width=14, joint="curve")
    d.text((60, 60), "ゼラチン ＝ コラーゲン", font=font("K", 44), fill=CREAM)
    d.text((60, 460), "フィルム感光層", font=font("B", 30), fill=GOLD); d.text((470, 460), "肌のハリ", font=font("B", 30), fill=RED2)
    d.text((330, 460), "→", font=font("B", 30), fill=CREAM)
    film_strip(d, 60, 510, 260, 70, frames=3)
    rounded(d, (470, 510, 720, 580), 12, fill=(245, 205, 190))
    return img

def illust_antiox():
    img, d = card_base((34, 20, 30)); img = glow(img, RED, (560, 330), 220, 150); d = ImageDraw.Draw(img)
    # faded photo vs vivid
    rounded(d, (50, 90, 330, 330), 14, fill=(200, 190, 170))
    rounded(d, (70, 110, 310, 290), 8, fill=(190, 170, 140)); d.ellipse([130, 140, 250, 260], fill=(205, 185, 150))
    d.text((60, 345), "色あせ（酸化）", font=font("B", 30), fill=GREY)
    rounded(d, (430, 90, 710, 330), 14, fill=(250, 250, 250))
    rounded(d, (450, 110, 690, 290), 8, fill=(90, 150, 210)); d.ellipse([510, 140, 630, 260], fill=(240, 180, 60))
    d.text((440, 345), "色あせを防ぐ", font=font("B", 30), fill=CREAM)
    d.polygon([(345, 200), (415, 200), (415, 185), (425, 210), (415, 235), (415, 220), (345, 220)], fill=GOLD)
    # astaxanthin molecule-ish
    cx, cy = 390, 480
    for i in range(7):
        x = 110 + i * 92; d.line([(x, cy + (18 if i % 2 else -18)), (x + 92, cy + (-18 if i % 2 else 18))], fill=RED2, width=9)
        d.ellipse([x - 12, cy + (18 if i % 2 else -18) - 12, x + 12, cy + (18 if i % 2 else -18) + 12], fill=RED)
    d.text((60, 530), "アスタキサンチン（赤い抗酸化成分）", font=font("B", 30), fill=RED2)
    return img

def illust_nano():
    img, d = card_base((22, 30, 44)); img = glow(img, MINT, (560, 300), 220, 60); d = ImageDraw.Draw(img)
    random.seed(3)
    # big clumpy particles left
    for _ in range(9):
        x, y, r = random.randint(80, 260), random.randint(130, 330), random.randint(28, 52)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(120, 130, 160))
    d.text((60, 370), "通常：粒子が大きい", font=font("B", 28), fill=GREY)
    d.polygon([(330, 230), (400, 230), (400, 215), (410, 240), (400, 265), (400, 250), (330, 250)], fill=GOLD)
    for _ in range(260):
        x, y, r = random.randint(450, 710), random.randint(110, 350), random.randint(3, 6)
        d.ellipse([x - r, y - r, x + r, y + r], fill=MINT)
    d.text((440, 370), "ナノ化：約20nm", font=font("K", 32), fill=MINT)
    # skin layers
    for i, c in enumerate([(240, 200, 185), (230, 175, 160), (215, 150, 140)]):
        rounded(d, (60, 440 + i * 40, 720, 440 + i * 40 + 36), 8, fill=c)
    for x in range(100, 700, 60):
        d.ellipse([x - 5, 452, x + 5, 462], fill=MINT); d.ellipse([x + 20, 492, x + 28, 500], fill=MINT)
    d.text((70, 560), "角層へ届きやすく、成分も安定", font=font("B", 26), fill=CREAM)
    return img

def illust_light():
    img, d = card_base((20, 24, 46)); img = glow(img, GOLD, (170, 150), 200, 120); d = ImageDraw.Draw(img)
    d.ellipse([110, 90, 230, 210], fill=(255, 210, 90))
    for a in range(0, 360, 30):
        x0 = 170 + 75 * math.cos(math.radians(a)); y0 = 150 + 75 * math.sin(math.radians(a))
        x1 = 170 + 105 * math.cos(math.radians(a)); y1 = 150 + 105 * math.sin(math.radians(a))
        d.line([(x0, y0), (x1, y1)], fill=(255, 210, 90), width=6)
    # 3 種類の紫外線（太陽 → ラベル → シールド → 肌）
    for i, (c, lab) in enumerate([((200, 120, 255), "UVB"), ((150, 90, 230), "UVA"), ((110, 60, 200), "Deep UV")]):
        y = 290 + i * 70
        d.line([(230, 200 + i * 20), (420, y)], fill=c, width=8)
        d.text((440, y - 18), lab, font=font("B", 24), fill=c)
        d.line([(560, y), (600, y)], fill=c, width=8)
    d.arc([590, 230, 770, 560], 110, 250, fill=MINT, width=16)   # シールド
    rounded(d, (690, 240, 750, 550), 18, fill=(240, 200, 185))     # 肌
    d.text((60, 480), "光を制御する知識\n→ 日焼け止め・トーンアップ", font=font("B", 30), fill=CREAM)
    return img

def illust_jelly():
    img, d = card_base((40, 20, 30)); img = glow(img, RED, (390, 320), 250, 140); d = ImageDraw.Draw(img)
    bottle(d, 290, 150, 200, 270, (190, 30, 60), cap=(250, 245, 240), shape="jar", label="JELLY\nAQUARYSTA", fnt=font("K", 20), label_color=RED)
    # jelly blob
    d.ellipse([110, 380, 290, 520], fill=(230, 60, 90)); d.ellipse([140, 400, 200, 440], fill=(255, 150, 170))
    d.text((60, 60), "赤いジェリー状の先行美容液", font=font("K", 38), fill=CREAM)
    rounded(d, (430, 420, 730, 560), 16, fill=(60, 30, 44))
    d.text((450, 435), "ヒト型ナノセラミド", font=font("B", 28), fill=GOLD)
    d.text((450, 480), "全国発明表彰 受賞", font=font("B", 28), fill=CREAM)
    d.text((450, 520), "美白タイプも（2021）", font=font("R", 24), fill=GREY)
    return img

def illust_serum():
    img, d = card_base((24, 24, 44)); img = glow(img, GOLD, (260, 300), 200, 70); img = glow(img, (90, 110, 220), (540, 300), 200, 90); d = ImageDraw.Draw(img)
    bottle(d, 190, 120, 110, 330, (245, 232, 200), cap=(230, 185, 90), label="THE\nSERUM\nAM", fnt=font("K", 18), label_color=(120, 90, 40))
    bottle(d, 470, 120, 110, 330, (70, 80, 150), cap=(30, 34, 60), label="THE\nSERUM\nPM", fnt=font("K", 18), label_color=(60, 60, 120))
    d.text((170, 470), "朝用", font=font("K", 34), fill=GOLD); d.text((460, 470), "夜用", font=font("K", 34), fill=(150, 170, 255))
    d.text((60, 50), "ナイアシンアミド配合・医薬部外品", font=font("K", 34), fill=CREAM)
    d.text((60, 530), "朝＋夜の2本で、しわ改善", font=font("B", 30), fill=CREAM)
    return img

def illust_duv():
    img, d = card_base((22, 28, 50)); img = glow(img, (255, 200, 90), (150, 130), 170, 110); d = ImageDraw.Draw(img)
    d.ellipse([90, 70, 210, 190], fill=(255, 215, 100))
    bottle(d, 300, 110, 150, 340, (250, 225, 225), cap=(230, 120, 140), shape="tube", label="D-UV\nSHIELD", fnt=font("K", 22), label_color=(200, 60, 90))
    bottle(d, 470, 150, 130, 300, (250, 250, 250), cap=(200, 200, 210), shape="tube", label="TONE\nUP", fnt=font("K", 22), label_color=(90, 90, 110))
    rounded(d, (60, 230, 250, 290), 12, fill=(70, 40, 120)); d.text((80, 240), "SPF50+ PA++++", font=font("K", 24), fill=WHITE)
    rounded(d, (60, 310, 250, 370), 12, fill=(110, 60, 200)); d.text((80, 320), "Deep UV 対応", font=font("K", 24), fill=WHITE)
    d.text((60, 480), "Pentawards 2025 銀賞（パッケージ）", font=font("B", 28), fill=GOLD)
    d.text((60, 530), "ローズ／ナチュラルホワイト", font=font("R", 26), fill=GREY)
    return img

def illust_supple():
    img, d = card_base((24, 34, 40)); img = glow(img, MINT, (500, 300), 220, 60); d = ImageDraw.Draw(img)
    bottle(d, 420, 110, 170, 330, (245, 245, 240), cap=(40, 120, 110), shape="jar", label="META\nBARRIER", fnt=font("K", 22), label_color=(30, 110, 100))
    random.seed(5)
    for _ in range(14):
        x, y = random.randint(90, 330), random.randint(300, 460)
        d.ellipse([x, y, x + 46, y + 28], fill=(250, 250, 250), outline=(200, 200, 210), width=2)
    d.text((60, 60), "機能性表示食品", font=font("K", 40), fill=CREAM)
    d.text((60, 130), "サラシア由来成分で\n糖の吸収を抑える", font=font("B", 30), fill=MINT)
    d.text((60, 520), "化粧品と並ぶ、通販の柱", font=font("B", 26), fill=GREY)
    return img

def illust_recent():
    img, d = card_base((30, 24, 44)); img = glow(img, RED, (600, 150), 180, 90); d = ImageDraw.Draw(img)
    # timeline
    d.line([(90, 300), (700, 300)], fill=GREY, width=6)
    for x, yr, lab, c in [(110, "2007", "アスタリフト\n誕生", CREAM), (250, "2019", "メンズ\n参入", MINT), (390, "2022", "若年層向け\nクレスク", MINT), (530, "2026", "新プロモー\nション", GOLD), (670, "2027", "20周年", RED2)]:
        d.ellipse([x - 16, 284, x + 16, 316], fill=c)
        d.text((x - 38, 220), yr, font=font("K", 30), fill=c)
        for k, ln in enumerate(lab.split("\n")):
            tw = d.textlength(ln, font=font("B", 22)); d.text((x - tw / 2, 335 + k * 30), ln, font=font("B", 22), fill=CREAM)
    d.text((60, 60), "ブランドを広げ、20周年へ", font=font("K", 40), fill=CREAM)
    rounded(d, (60, 450, 720, 560), 16, fill=(50, 30, 50))
    d.text((80, 470), "「一生もののサイエンス」", font=font("K", 34), fill=GOLD)
    d.text((80, 520), "2026年秋 プロモーション", font=font("R", 24), fill=GREY)
    return img

def illust_issue():
    img, d = card_base((34, 26, 30))
    bars = [("競合大手", 0.9, (90, 96, 130)), ("インバウンド変動", 0.7, (90, 96, 130)), ("グループ内優先度", 0.6, (90, 96, 130))]
    for i, (lab, v, c) in enumerate(bars):
        y = 110 + i * 110
        d.text((60, y - 40), lab, font=font("B", 28), fill=CREAM)
        rounded(d, (60, y, 720, y + 40), 12, fill=(50, 52, 72))
        rounded(d, (60, y, 60 + 660 * v, y + 40), 12, fill=RED if i == 0 else c)
    rounded(d, (60, 450, 720, 560), 16, fill=(60, 36, 44))
    d.text((80, 465), "方針：規模より「収益性」と「ブランド価値」", font=font("K", 30), fill=GOLD)
    d.text((80, 512), "科学的な裏付けを前面に出す", font=font("R", 26), fill=GREY)
    return img

def illust_outro():
    img, d = card_base((28, 20, 36)); img = glow(img, RED, (390, 300), 260, 110); d = ImageDraw.Draw(img)
    items = [("コラーゲン", GOLD), ("抗酸化", RED2), ("ナノ技術", MINT), ("光の制御", (255, 215, 100))]
    for i, (s, c) in enumerate(items):
        x = 60 + (i % 2) * 340; y = 70 + (i // 2) * 150
        rounded(d, (x, y, x + 300, y + 110), 18, fill=(40, 34, 56), outline=c, width=4)
        tw = d.textlength(s, font=font("K", 36)); d.text((x + (300 - tw) / 2, y + 30), s, font=font("K", 36), fill=c)
    d.text((60, 400), "写真の技術 → 肌の科学", font=font("K", 44), fill=CREAM)
    d.text((60, 480), "チャンネル登録・高評価をお願いします", font=font("B", 28), fill=GREY)
    return img

ILLUST = {f.__name__.replace("illust_", ""): f for f in [illust_intro, illust_film_crash, illust_org, illust_collagen, illust_antiox,
          illust_nano, illust_light, illust_jelly, illust_serum, illust_duv, illust_supple, illust_recent, illust_issue, illust_outro]}

def draw_scene(i, sc):
    img = gradient_bg(NAVY, NAVY2)
    d = ImageDraw.Draw(img)
    # left accent bar + chapter number
    d.rectangle([0, 0, 18, H], fill=RED)
    d.text((70, 60), f"{i:02d} / {len(SCENES) - 1:02d}", font=font("B", 30), fill=GREY)
    d.text((W - 420, 60), "富士フイルムの化粧品事業", font=font("B", 28), fill=GREY)
    # title
    ty = 150
    if sc["illust"] == "intro":
        ty += 30
        d.text((70, ty), sc["title"], font=font("K", 86), fill=WHITE)
        d.text((70, ty + 140), sc["sub"], font=font("B", 44), fill=GOLD)
        d.text((70, ty + 260), "3分でわかる", font=font("K", 60), fill=RED2)
    else:
        th = text_fit(d, (70, ty), sc["title"], font("K", 66), WHITE, 980)
        uy = ty + th + 22
        d.rounded_rectangle((70, uy, 70 + 140, uy + 8), radius=4, fill=RED)
        h = text_fit(d, (70, uy + 35), sc["sub"], font("B", 36), GOLD, 960)
        by = uy + 50 + h + 20
        for b in sc["bullets"]:
            d.ellipse([74, by + 18, 94, by + 38], fill=RED2)
            hh = text_fit(d, (115, by), b, font("R", 34), CREAM, 880)
            by += hh + 22
    # illustration card (right)
    card = ILLUST[sc["illust"]]()
    sx, sy = 1100, 150
    shadow = Image.new("RGBA", (CW + 60, CH + 60), (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    rounded(sd, (30, 30, CW + 30, CH + 30), 34, fill=(0, 0, 0, 150)); shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    img.paste(shadow, (sx - 30, sy - 30 + 18), shadow)
    img.paste(card, (sx, sy), card)
    # caption band (subtitles are burned later by ffmpeg; leave bottom area darker)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rectangle([0, H - 200, W, H], fill=(0, 0, 0, 90))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    return img

for i, sc in enumerate(SCENES):
    im = draw_scene(i, sc)
    im.save(os.path.join(OUT_DIR, f"{i:02d}_{sc['id']}.png"))
    print("slide", i, sc["id"])
