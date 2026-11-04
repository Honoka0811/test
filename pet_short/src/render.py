"""Render the vertical short video frames and pipe to ffmpeg.
usage: python3 render.py out.mp4 [--preview t1,t2,...]
"""
import json, math, os, sys, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scenes import SCENES, MAX_PRICE

D = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
A = os.path.join(D, "assets")
F_DISPLAY = f"{A}/expo-google-fonts-dela-gothic-one-0.4.1/package/400Regular/DelaGothicOne_400Regular.ttf"
F_ROUND = f"{A}/expo-google-fonts-m-plus-rounded-1c-0.4.4/package/900Black/MPLUSRounded1c_900Black.ttf"
F_ROUND8 = f"{A}/expo-google-fonts-m-plus-rounded-1c-0.4.4/package/800ExtraBold/MPLUSRounded1c_800ExtraBold.ttf"

TIM = json.load(open(os.path.join(D, "timing.json")))
TOTAL = TIM["total"]
SC = {s["id"]: s for s in SCENES}

# ---------------- helpers ----------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d)
def e_out(x): return 1 - (1 - x) ** 3
def e_back(x, s=1.9):
    x -= 1; return x * x * ((s + 1) * x + s) + 1
def e_elastic(x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi / 3)) + 1

_font = {}
def font(p, s):
    k = (p, s)
    if k not in _font: _font[k] = ImageFont.truetype(p, s)
    return _font[k]

_txt = {}
def text_img(text, fp, size, fill=(255, 255, 255), strokes=((14, (20, 20, 40)),), shadow=True, spacing=10, align="center"):
    """Render text with multiple outlines (outermost first). Cached."""
    k = (text, fp, size, fill, strokes, shadow)
    if k in _txt: return _txt[k]
    f = font(fp, size)
    maxw = max(s[0] for s in strokes) if strokes else 0
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bb = dummy.multiline_textbbox((0, 0), text, font=f, spacing=spacing, align=align, stroke_width=maxw)
    pad = maxw + 20
    w, h = int(bb[2] - bb[0] + pad * 2), int(bb[3] - bb[1] + pad * 2)
    im = Image.new("RGBA", (w, h + 12), (0, 0, 0, 0))
    org = (int(pad - bb[0]), int(pad - bb[1]))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text((org[0] + 6, org[1] + 10), text, font=f, fill=(0, 0, 0, 120),
                                          spacing=spacing, align=align, stroke_width=maxw, stroke_fill=(0, 0, 0, 120))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im)
    for sw, sc in strokes:
        d.multiline_text(org, text, font=f, fill=sc, spacing=spacing, align=align, stroke_width=sw, stroke_fill=sc)
    d.multiline_text(org, text, font=f, fill=fill, spacing=spacing, align=align)
    _txt[k] = im
    return im

_emo = {}
def emoji(code):
    if code not in _emo:
        _emo[code] = Image.open(f"{A}/png/{code}.png").convert("RGBA")
    return _emo[code]

def paste(canvas, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01: return
    w, h = img.size
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    im = img.resize((nw, nh), Image.BILINEAR) if (nw, nh) != (w, h) else img
    if rot: im = im.rotate(rot, Image.BILINEAR, expand=True)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2))) if (
        0 <= int(cx - im.width / 2) and 0 <= int(cy - im.height / 2) and
        int(cx - im.width / 2) + im.width <= W and int(cy - im.height / 2) + im.height <= H) else _paste_clip(canvas, im, int(cx - im.width / 2), int(cy - im.height / 2))

def _paste_clip(canvas, im, x, y):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(im, (x, y), im)
    canvas.alpha_composite(layer)

def rrect(canvas, box, r, fill, outline=None, width=0):
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle(box, r, fill=fill, outline=outline, width=width)
    canvas.alpha_composite(lay)

# ---------------- background ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
CX, CY = W / 2, H * 0.36
ANG = np.arctan2(yy - CY, xx - CX)
RAD = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2) / 1300.0
VIG = np.clip(1.0 - 0.55 * RAD ** 1.6, 0.25, 1.0)[..., None]

def sunburst(c1, c2, t, rays=18, speed=0.25):
    m = (np.sin(ANG * rays + t * speed * 2 * math.pi) > 0).astype(np.float32)[..., None]
    a = np.array(c1, np.float32); b = np.array(c2, np.float32)
    img = a * m + b * (1 - m)
    glow = np.exp(-(RAD * 2.2) ** 2)[..., None] * 70
    img = (img + glow) * VIG
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

def stripes(c1, c2, t):
    m = ((((xx + yy * 0.6) + t * 120) % 160) < 80).astype(np.float32)[..., None]
    img = np.array(c1, np.float32) * m + np.array(c2, np.float32) * (1 - m)
    img = img * VIG
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

# ---------------- particles ----------------
def confetti(canvas, lt, seed=1, n=90, t0=0.0):
    r = random.Random(seed)
    d = ImageDraw.Draw(canvas)
    cols = [(255, 80, 80), (255, 220, 60), (80, 200, 255), (120, 255, 140), (255, 120, 220), (255, 255, 255)]
    for i in range(n):
        x0 = r.uniform(0, W); vy = r.uniform(250, 520); vx = r.uniform(-120, 120)
        delay = r.uniform(0, 0.8); sz = r.uniform(14, 28); spin = r.uniform(2, 8); c = r.choice(cols)
        tt = lt - t0 - delay
        if tt < 0: continue
        x = x0 + vx * tt + 40 * math.sin(tt * spin)
        y = -40 + vy * tt + 120 * tt * tt
        if y > H + 40: continue
        ww = sz * abs(math.cos(tt * spin))
        d.rectangle([x - ww / 2, y - sz / 3, x + ww / 2, y + sz / 3], fill=c)

def burst_stars(canvas, cx, cy, lt, n=12, seed=3):
    if lt < 0 or lt > 0.7: return
    r = random.Random(seed)
    star = emoji("2728")
    for i in range(n):
        a = 2 * math.pi * i / n + r.uniform(-0.2, 0.2)
        dist = 120 + 380 * e_out(lt / 0.7)
        paste(canvas, star, cx + math.cos(a) * dist, cy + math.sin(a) * dist, 0.13, 0, 1 - lt / 0.7)

# ---------------- common UI ----------------
def subtitle(canvas, sc_t, lt):
    cur = None
    for s in sc_t["sents"]:
        if s["start"] - 0.05 <= lt < s["start"] + s["dur"] + 0.15:
            cur = s
    if not cur: return
    p = prog(lt, cur["start"] - 0.05, 0.12)
    im = text_img(cur["sub"], F_ROUND, 72, fill=(255, 255, 255), strokes=((14, (30, 20, 60)),), spacing=14, shadow=False)
    sc = 0.85 + 0.15 * e_back(p)
    bw, bh = im.width / 2 - 10, im.height / 2 - 18
    rrect(canvas, (W / 2 - bw, 1530 - bh, W / 2 + bw, 1530 + bh), 30, (0, 0, 0, int(110 * p)))
    paste(canvas, im, W / 2, 1530, sc, 0, p)

def header(canvas, text="生涯コスト ランキング"):
    im = text_img("🐾 " if False else text, F_ROUND, 52, fill=(255, 255, 255), strokes=((10, (40, 30, 80)),), shadow=False)
    rrect(canvas, (W / 2 - im.width / 2 - 30, 128, W / 2 + im.width / 2 + 30, 222), 47, (30, 20, 60, 190))
    paste(canvas, im, W / 2 + 30, 172)
    paste(canvas, emoji("1f43e"), W / 2 - im.width / 2 + 20, 175, 0.12)

def progress(canvas, t):
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, 14], fill=(0, 0, 0, 120))
    d.rectangle([0, 0, int(W * t / TOTAL), 14], fill=(255, 225, 60))

def credit(canvas):
    im = text_img("VOICEVOX:四国めたん", F_ROUND8, 30, fill=(255, 255, 255), strokes=((5, (0, 0, 0)),), shadow=False)
    paste(canvas, im, W - im.width / 2 - 20, 60, 1.0, 0, 0.85)

def wipe(canvas, lt, color=(255, 255, 255)):
    # diagonal band sweeping across during first 0.22s
    p = lt / 0.22
    if p >= 1: return
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = -W * 0.6 + p * W * 2.4
    d.polygon([(x, 0), (x + 500, 0), (x + 500 - 700, H), (x - 700, H)], fill=color + (235,))
    canvas.alpha_composite(lay)

def flash(canvas, lt, t0=0.0, dur=0.25, strength=230):
    p = (lt - t0) / dur
    if 0 <= p < 1:
        canvas.alpha_composite(Image.new("RGBA", canvas.size, (255, 255, 255, int(strength * (1 - p)))))

# ---------------- scenes ----------------
RANK_COL = {6: (255, 255, 255), 5: (255, 255, 255), 4: (255, 255, 255), 3: (255, 240, 120), 2: (230, 230, 245), 1: (255, 215, 60)}

def fmt_price(lo, hi, p):
    v = hi * e_out(p)
    if lo is None: return f"約{int(round(v))}万円"
    vlo = lo * e_out(p)
    return f"約{int(round(vlo))}〜{int(round(v))}万円"

def scene_rank(canvas, cfg, st, lt, t):
    c1, c2 = cfg["colors"]
    bg = sunburst(c1, c2, t)
    canvas.alpha_composite(bg)
    header(canvas)
    champion = cfg.get("champion")
    # rank slam
    p = prog(lt, 0.0, 0.32)
    sc = 2.6 - 1.6 * e_back(p, 1.4) if p < 1 else 1.0
    rk = text_img(f"第{cfg['rank']}位", F_DISPLAY, 190, fill=RANK_COL[cfg["rank"]],
                  strokes=((26, (255, 255, 255)), (16, (200, 30, 40))))
    pulse = 1 + 0.03 * math.sin(lt * 6) if p >= 1 else 1
    paste(canvas, rk, W / 2, 400, sc * pulse, -4, clamp(p * 3))
    if champion and lt > 0.3:
        paste(canvas, emoji("1f451"), W / 2 + 250, 300 + 8 * math.sin(lt * 5), 0.42 * e_back(prog(lt, 0.3, 0.4)), -18)
    # emoji pop
    p = prog(lt, 0.3, 0.55)
    if p > 0:
        es = e_elastic(p)
        bob = 14 * math.sin(lt * 4.2)
        lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        r = 210 * es
        ImageDraw.Draw(lay).ellipse([W / 2 - r, 690 - r, W / 2 + r, 690 + r], fill=(255, 255, 255, 235))
        canvas.alpha_composite(lay)
        paste(canvas, emoji(cfg["emoji"]), W / 2, 690 + bob, 0.66 * es, 6 * math.sin(lt * 3))
        burst_stars(canvas, W / 2, 690, lt - 0.3)
    # name
    p = prog(lt, 0.45, 0.3)
    nm = text_img(cfg["name"], F_DISPLAY, 112, fill=(255, 255, 255), strokes=((16, (30, 20, 60)),))
    paste(canvas, nm, W / 2 + (1 - e_out(p)) * 500, 960, 1.0, 0, p)
    # price counter
    p = prog(lt, 0.7, 0.8)
    if lt > 0.65:
        lo, hi = cfg["price"]
        ptxt = fmt_price(lo, hi, p)
        size = 128 if lo is not None else 150
        pi = text_img(ptxt, F_DISPLAY, size, fill=(255, 236, 60), strokes=((24, (255, 255, 255)), (14, (210, 20, 40))))
        pop = 1 + 0.18 * (1 - prog(lt, 1.5, 0.25)) if lt > 1.5 else 1.0
        fit = min(1.0, 960 / pi.width)
        paste(canvas, pi, W / 2, 1100, fit * pop * (0.6 + 0.4 * e_back(prog(lt, 0.65, 0.2))))
        if 1.5 <= lt < 2.1:
            burst_stars(canvas, W / 2, 1100, lt - 1.5, 10, 9)
    # cost bar
    p = prog(lt, 0.8, 1.0)
    if lt > 0.75:
        x0, x1, y = 110, W - 110, 1225
        rrect(canvas, (x0, y - 22, x1, y + 22), 22, (20, 15, 45, 200), (255, 255, 255, 255), 5)
        frac = cfg["price"][1] / MAX_PRICE * e_out(p)
        if frac > 0.02:
            col = (255, 70, 70) if frac > 0.5 else (255, 190, 40)
            rrect(canvas, (x0 + 7, y - 15, x0 + 7 + (x1 - x0 - 14) * frac, y + 15), 15, col + (255,))
        lab = text_img("💰", F_ROUND, 10) if False else None
        paste(canvas, emoji("1f4b0"), x0 + 7 + (x1 - x0 - 14) * frac, y - 4, 0.15)
    # chips
    for i, (txt, tt0) in enumerate(((cfg["month"], 1.15), (cfg["life"], 1.35))):
        p = prog(lt, tt0, 0.3)
        if p <= 0: continue
        hl = cfg.get("surprise") and i == 1
        ch = text_img(txt, F_ROUND, 46, fill=(255, 255, 255) if not hl else (255, 240, 80),
                      strokes=((8, (30, 20, 60)),), shadow=False)
        cx = W / 2 + (-1 if i == 0 else 1) * 240
        cx += (1 - e_out(p)) * (-600 if i == 0 else 600)
        bw = ch.width / 2 + 10
        rrect(canvas, (cx - bw, 1325 - 46, cx + bw, 1325 + 46), 46, ((30, 20, 60, 210) if not hl else (220, 20, 60, 235)))
        paste(canvas, ch, cx, 1322, 1.0 + (0.08 * math.sin(lt * 10) if hl else 0))
    # surprise stamp
    if cfg.get("surprise"):
        p = prog(lt, 0.55, 0.25)
        if p > 0:
            stp = text_img("意外!?", F_DISPLAY, 120, fill=(255, 255, 255), strokes=((14, (230, 20, 50)),))
            paste(canvas, stp, 840, 600, 2.4 - 1.4 * e_out(p), 14, p)
            if lt < 1.5:
                paste(canvas, emoji("1f631"), 230, 600, 0.34 * e_back(prog(lt, 0.6, 0.3)), -10)
    if champion:
        confetti(canvas, lt, seed=11, n=110, t0=0.05)
    subtitle(canvas, st, lt)
    flash(canvas, lt, 0.12, 0.22, 200 if not champion else 255)

def scene_hook(canvas, st, lt, t):
    canvas.alpha_composite(sunburst((120, 40, 200), (70, 20, 150), t, 20, 0.4))
    # floating animals around
    codes = ["1f436", "1f431", "1f420", "1f422", "1f439", "1f99c"]
    for i, c in enumerate(codes):
        a = 2 * math.pi * i / 6 + lt * 0.6
        rx, ry = 390, 300
        x = W / 2 + rx * math.cos(a); y = 760 + ry * math.sin(a)
        p = prog(lt, 0.05 * i, 0.4)
        paste(canvas, emoji(c), x, y, 0.36 * e_back(p), 10 * math.sin(lt * 3 + i))
    # falling money
    r = random.Random(5)
    for i in range(14):
        x0 = r.uniform(40, W - 40); sp = r.uniform(250, 450); d0 = r.uniform(0, 3)
        y = ((lt + d0) * sp) % (H + 200) - 100
        paste(canvas, emoji("1f4b8"), x0, y, 0.16, 20 * math.sin(lt * 3 + i), 0.85)
    # big question
    p = prog(lt, 0.0, 0.35)
    t1 = text_img("ペットの一生", F_DISPLAY, 140, fill=(255, 255, 255), strokes=((20, (40, 10, 90)),))
    t2 = text_img("いくらかかる？", F_DISPLAY, 150, fill=(255, 236, 60), strokes=((24, (255, 255, 255)), (14, (220, 20, 60))))
    pulse = 1 + 0.04 * math.sin(lt * 7)
    paste(canvas, t1, W / 2, 380, (2.2 - 1.2 * e_back(p)), -3, clamp(p * 2))
    p2 = prog(lt, 0.35, 0.35)
    paste(canvas, t2, W / 2, 760, (2.2 - 1.2 * e_back(p2)) * pulse, 3, clamp(p2 * 2))
    # teaser card for 2nd sentence
    s2 = st["sents"][1]["start"]
    p3 = prog(lt, s2, 0.3)
    if p3 > 0:
        q = text_img("第3位に\n意外な動物!?", F_DISPLAY, 92, fill=(255, 255, 255), strokes=((14, (230, 20, 50)),), spacing=16)
        paste(canvas, q, W / 2, 1130, 0.5 + 0.5 * e_back(p3), -4 + 2 * math.sin(lt * 9))
        paste(canvas, emoji("2753"), W / 2 + 330, 1070, 0.3 * e_back(p3), 15)
    subtitle(canvas, st, lt)
    flash(canvas, lt, 0.0, 0.2)

def scene_title(canvas, st, lt, t):
    canvas.alpha_composite(sunburst((255, 70, 110), (230, 30, 80), t, 24, 0.6))
    p = prog(lt, 0.05, 0.35)
    a = text_img("ペット", F_DISPLAY, 150, fill=(255, 255, 255), strokes=((20, (120, 10, 40)),))
    b = text_img("生涯コスト", F_DISPLAY, 170, fill=(255, 236, 60), strokes=((26, (255, 255, 255)), (16, (200, 20, 50))))
    c = text_img("ランキング", F_DISPLAY, 170, fill=(255, 255, 255), strokes=((20, (120, 10, 40)),))
    paste(canvas, a, W / 2 - (1 - e_out(p)) * 900, 520, 1, -4)
    paste(canvas, b, W / 2, 760, 0.3 + 0.7 * e_back(prog(lt, 0.2, 0.35)), 0)
    paste(canvas, c, W / 2 + (1 - e_out(prog(lt, 0.35, 0.35))) * 900, 1000, 1, 4)
    paste(canvas, emoji("1f451"), W / 2, 300 + 10 * math.sin(lt * 5), 0.5 * e_back(prog(lt, 0.4, 0.4)))
    flash(canvas, lt, 0.0, 0.2)

def scene_drumroll(canvas, st, lt, t):
    shake = 6 * clamp(lt / st["dur"])
    canvas.alpha_composite(sunburst((60, 50, 90), (25, 20, 45), t, 30, 1.5 + lt))
    a = text_img("第1位は…", F_DISPLAY, 180, fill=(255, 215, 60), strokes=((26, (255, 255, 255)), (16, (200, 30, 40))))
    p = prog(lt, 0.0, 0.3)
    paste(canvas, a, W / 2 + random.uniform(-shake, shake), 520 + random.uniform(-shake, shake), 0.5 + 0.5 * e_back(p))
    # silhouette (black) emoji with ?
    sil = emoji("1f436").copy()
    blk = Image.new("RGBA", sil.size, (10, 10, 20, 255)); blk.putalpha(sil.getchannel("A"))
    z = 0.7 + 0.08 * clamp(lt / st["dur"])
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([W / 2 - 230, 900 - 230, W / 2 + 230, 900 + 230], fill=(255, 255, 255, 200))
    canvas.alpha_composite(lay)
    paste(canvas, blk, W / 2 + random.uniform(-shake, shake), 900, z)
    paste(canvas, emoji("2753"), W / 2 + 250, 720, 0.32 + 0.04 * math.sin(lt * 12), 12)
    paste(canvas, emoji("1f941"), W / 2 - 280, 1180, 0.3 + 0.04 * abs(math.sin(lt * 25)))
    subtitle(canvas, st, lt)

def scene_warn(canvas, st, lt, t):
    canvas.alpha_composite(stripes((210, 25, 45), (160, 10, 30), t))
    # warning tape band
    p = prog(lt, 0.0, 0.3)
    tape = Image.new("RGBA", (1600, 110), (255, 215, 0, 255))
    dd = ImageDraw.Draw(tape)
    for i in range(-2, 30):
        x = i * 90 - (lt * 200) % 90
        dd.polygon([(x, 0), (x + 45, 0), (x - 10, 110), (x - 55, 110)], fill=(20, 20, 20, 255))
    paste(canvas, tape, W / 2, 280, 1.0, 6, p)
    a = text_img("最大の落とし穴", F_DISPLAY, 140, fill=(255, 255, 255), strokes=((20, (90, 0, 10)),))
    paste(canvas, a, W / 2, 470, 2.0 - 1.0 * e_back(prog(lt, 0.1, 0.3)), -3, prog(lt, 0.1, 0.1))
    s1 = st["sents"][1]["start"]
    p1 = prog(lt, s1, 0.5)
    if p1 > 0:
        lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        r = 220 * e_elastic(p1)
        ImageDraw.Draw(lay).ellipse([W / 2 - r, 800 - r, W / 2 + r, 800 + r], fill=(255, 255, 255, 240))
        canvas.alpha_composite(lay)
        paste(canvas, emoji("1f3e5"), W / 2, 800 + 10 * math.sin(lt * 4), 0.66 * e_elastic(p1))
    s2 = st["sents"][2]["start"]
    p2 = prog(lt, s2, 0.3)
    if p2 > 0:
        jit = 5 * math.sin(lt * 40) if lt - s2 < 0.6 else 0
        b = text_img("治療費 1回で\n数万〜数十万円!", F_DISPLAY, 92, fill=(255, 236, 60),
                     strokes=((22, (255, 255, 255)), (13, (190, 0, 30))), spacing=16)
        paste(canvas, b, W / 2 + jit, 1140, 0.4 + 0.6 * e_back(p2), -2)
    s3 = st["sents"][3]["start"]
    p3 = prog(lt, s3, 0.3)
    if p3 > 0:
        c = text_img("ペット保険も検討!", F_ROUND, 56, fill=(255, 255, 255), strokes=((9, (30, 20, 60)),), shadow=False)
        rrect(canvas, (W / 2 - c.width / 2 - 20, 1365 - 48, W / 2 + c.width / 2 + 20, 1365 + 48), 48, (30, 120, 220, 240))
        paste(canvas, c, W / 2 + (1 - e_out(p3)) * 700, 1362)
        paste(canvas, emoji("1f4a1"), W / 2 + c.width / 2 + 10, 1300, 0.2 * e_back(p3), 15)
    subtitle(canvas, st, lt)
    flash(canvas, lt, 0.0, 0.25, 255)

def scene_cta(canvas, st, lt, t):
    canvas.alpha_composite(sunburst((30, 200, 190), (10, 140, 160), t, 18, 0.3))
    header(canvas, "まとめ")
    rows = [(1, "1f436", "犬", "約250万円"), (2, "1f431", "猫", "約150万円"), (3, "1f422", "カメ", "約50〜150万円"),
            (4, "1f99c", "インコ", "約30〜60万円"), (5, "1f420", "熱帯魚", "約5〜20万円"), (6, "1f439", "ハムスター", "約10万円")]
    for i, (rk, code, nm, pr) in enumerate(rows):
        p = prog(lt, 0.08 * i, 0.3)
        if p <= 0: continue
        y = 310 + i * 132
        x = (1 - e_out(p)) * -W
        rrect(canvas, (x + 70, y - 56, x + W - 70, y + 56), 56, (255, 255, 255, 235))
        medal = {1: (255, 200, 30), 2: (190, 195, 210), 3: (215, 130, 60)}.get(rk, (90, 90, 130))
        lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse([x + 82, y - 46, x + 174, y + 46], fill=medal + (255,))
        canvas.alpha_composite(lay)
        paste(canvas, text_img(str(rk), F_DISPLAY, 60, fill=(255, 255, 255), strokes=((6, (40, 30, 60)),), shadow=False), x + 128, y - 2)
        paste(canvas, emoji(code), x + 245, y, 0.17)
        nmi = text_img(nm, F_ROUND, 56, fill=(40, 30, 70), strokes=(), shadow=False)
        paste(canvas, nmi, x + 315 + nmi.width / 2, y - 4)
        pri = text_img(pr, F_DISPLAY, 54, fill=(220, 30, 60), strokes=(), shadow=False)
        paste(canvas, pri, x + W - 100 - pri.width / 2, y - 2)
    note = text_img("※金額は目安（ペットフード協会の調査等をもとに概算）", F_ROUND8, 30, fill=(255, 255, 255),
                    strokes=((5, (0, 60, 70)),), shadow=False)
    paste(canvas, note, W / 2, 1110, 1, 0, prog(lt, 0.6, 0.3))
    s1 = st["sents"][1]["start"]
    p = prog(lt, s1, 0.35)
    if p > 0:
        c = text_img("コメントで教えてね!", F_DISPLAY, 84, fill=(255, 255, 255), strokes=((14, (220, 40, 90)),))
        paste(canvas, c, W / 2, 1250, (0.4 + 0.6 * e_back(p)) * (1 + 0.04 * math.sin(lt * 8)))
        paste(canvas, emoji("1f4ac"), W / 2 + c.width / 2 - 10, 1180, 0.22 * e_back(p), 10)
    subtitle(canvas, st, lt)
    flash(canvas, lt, 0.0, 0.2)
    if lt > st["dur"] - 1.2:
        confetti(canvas, lt, seed=4, n=60, t0=st["dur"] - 1.2)

# ---------------- frame ----------------
def frame(t):
    sc_t = None
    for s in TIM["scenes"]:
        if s["start"] <= t < s["start"] + s["dur"]:
            sc_t = s
    if sc_t is None: sc_t = TIM["scenes"][-1]
    lt = t - sc_t["start"]
    cfg = SC[sc_t["id"]]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    k = cfg["kind"]
    if k == "rank": scene_rank(canvas, cfg, sc_t, lt, t)
    elif k == "hook": scene_hook(canvas, sc_t, lt, t)
    elif k == "title": scene_title(canvas, sc_t, lt, t)
    elif k == "drumroll": scene_drumroll(canvas, sc_t, lt, t)
    elif k == "warn": scene_warn(canvas, sc_t, lt, t)
    elif k == "cta": scene_cta(canvas, sc_t, lt, t)
    if k not in ("hook",):
        wipe(canvas, lt)
    progress(canvas, t)
    credit(canvas)
    img = canvas.convert("RGB")
    # screen shake on impacts
    sh = 0
    if k == "rank" and 0.12 <= lt < 0.45: sh = 18 * (1 - (lt - 0.12) / 0.33)
    if k == "warn" and lt < 0.4: sh = 16 * (1 - lt / 0.4)
    if sh:
        r = random.Random(int(t * 1000))
        dx, dy = int(r.uniform(-sh, sh)), int(r.uniform(-sh, sh))
        img = img.transform(img.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), fillcolor=(0, 0, 0))
        img = img.resize((int(W * 1.03), int(H * 1.03))).crop((int(W * .015), int(H * .015), int(W * .015) + W, int(H * .015) + H))
    return img


def main():
    out = sys.argv[1]
    if "--preview" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
        for t in ts:
            frame(t).save(f"{out}_{t:05.2f}.png")
        return
    n = int(math.ceil(TOTAL * FPS))
    a, b = 0, n
    if "--part" in sys.argv:
        k, m = map(int, sys.argv[sys.argv.index("--part") + 1].split("/"))
        a, b = n * k // m, n * (k + 1) // m
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(a, b):
        ff.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0: print(f"{i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    print("done", out)


if __name__ == "__main__":
    main()
