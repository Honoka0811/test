# 1080x1920 / 30fps の縦型ショート動画のフレームをPILで描画し、ffmpegで書き出す
import json, math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from script import DISCLAIMER

W, H, FPS = 1080, 1920, 30
tl = json.load(open("build/timeline.json"))
TOTAL = tl["total"]
SC = tl["scenes"]

F_BLACK = "assets/NotoSansJP-Black.ttf"
F_ROUND = "assets/MPlusRounded-XB.ttf"
F_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
_fc = {}


def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]


GOLD = (255, 200, 60)
GOLD2 = (255, 150, 20)
WHITE = (255, 255, 255)
RED = (255, 70, 90)
GREEN = (60, 230, 140)
INK = (10, 14, 26)
EMOJI = {1: "💰", 2: "📒", 3: "⏳", 4: "📚", 5: "📈"}
rng = np.random.default_rng(3)


# ---------- イージング ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(x, s=1.9):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


# ---------- 背景(静的レイヤーを事前生成) ----------
def make_bg():
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([8, 12, 28]), np.array([18, 30, 58])
    arr = (top * (1 - y) + bot * y)[:, None, :].repeat(W, 1).reshape(H, W, 3)
    # ビネット
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
    arr *= (1 - np.clip(r - 0.25, 0, 1) * 1.1)[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    for x in range(0, W, 90):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 10), width=1)
    for yv in range(0, H, 90):
        d.line([(0, yv), (W, yv)], fill=(255, 255, 255, 10), width=1)
    return im


BG = make_bg()

# 背景のローソク足(右肩上がり)
CANDLES = []
p = 0.0
for i in range(40):
    o = p
    p = p + rng.normal(0.35, 1.0)
    hi, lo = max(o, p) + abs(rng.normal(0, 0.5)), min(o, p) - abs(rng.normal(0, 0.5))
    CANDLES.append((o, p, hi, lo))
cmin = min(c[3] for c in CANDLES); cmax = max(c[2] for c in CANDLES)


def draw_candles(img, t):
    lay = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(lay)
    cw = 46
    scroll = (t * 28) % cw
    shown = int(min(len(CANDLES), 8 + t * 1.2))
    def Y(v):
        return int(H * 0.82 - (v - cmin) / (cmax - cmin) * H * 0.55)
    pts = []
    for i in range(shown):
        o, c, hi, lo = CANDLES[i]
        x = int(i * cw - scroll - (shown - 22) * cw * (shown > 22))
        if x < -cw or x > W + cw:
            continue
        col = (60, 230, 140, 38) if c >= o else (255, 80, 100, 38)
        d.line([(x + cw // 2 - 6, Y(hi)), (x + cw // 2 - 6, Y(lo))], fill=col, width=3)
        d.rectangle([x + 6, min(Y(o), Y(c)), x + cw - 18, max(Y(o), Y(c)) + 2], fill=col)
        pts.append((x + cw // 2 - 6, Y(c)))
    if len(pts) > 1:
        d.line(pts, fill=(255, 200, 60, 45), width=5)
    img.alpha_composite(lay)


# 浮かぶ粒子(金の光)
PARTS = [dict(x=rng.uniform(0, W), y0=rng.uniform(0, H), sp=rng.uniform(30, 110),
              r=rng.uniform(2, 7), ph=rng.uniform(0, 6.28)) for _ in range(55)]


def draw_particles(img, t, boost=1.0):
    lay = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(lay)
    for p in PARTS:
        y = (p["y0"] - t * p["sp"] * boost) % (H + 40) - 20
        x = p["x"] + math.sin(t * 1.3 + p["ph"]) * 20
        a = int(90 + 80 * math.sin(t * 3 + p["ph"]))
        r = p["r"]
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 210, 90, a))
    img.alpha_composite(lay)


# ---------- テキスト描画ユーティリティ ----------
def text_layer(txt, size, fill=WHITE, stroke=10, stroke_fill=INK, fpath=F_BLACK,
               grad=None, shadow=True, maxw=W - 90):
    f = font(fpath, size)
    while f.getlength(txt) > maxw and size > 30:
        size -= 4; f = font(fpath, size)
    bb = f.getbbox(txt, stroke_width=stroke)
    w, h = bb[2] - bb[0] + 30, bb[3] - bb[1] + 30
    lay = Image.new("RGBA", (w, h + 14))
    d = ImageDraw.Draw(lay)
    org = (15 - bb[0], 15 - bb[1])
    if shadow:
        d.text((org[0], org[1] + 10), txt, font=f, fill=(0, 0, 0, 150),
               stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    d.text(org, txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    if grad:
        mask = Image.new("L", lay.size)
        ImageDraw.Draw(mask).text(org, txt, font=f, fill=255)
        g = np.linspace(0, 1, lay.size[1])[:, None, None]
        c1, c2 = np.array(grad[0]), np.array(grad[1])
        ga = (c1 * (1 - g) + c2 * g).repeat(lay.size[0], 1).astype(np.uint8)
        gi = Image.fromarray(ga).convert("RGBA")
        lay.paste(gi, (0, 0), mask)
    return lay


def emoji_layer(ch, size):
    f = font(F_EMOJI, 109)
    im = Image.new("RGBA", (140, 140))
    ImageDraw.Draw(im).text((8, 4), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((size, int(size * im.size[1] / im.size[0])), Image.LANCZOS)


def paste_c(img, lay, cx, cy, scale=1.0, alpha=1.0, rot=0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if scale != 1.0:
        lay = lay.resize((max(1, int(lay.size[0] * scale)), max(1, int(lay.size[1] * scale))),
                         Image.BILINEAR)
    if rot:
        lay = lay.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1:
        a = lay.split()[3].point(lambda v: int(v * alpha))
        lay = lay.copy(); lay.putalpha(a)
    img.alpha_composite(lay, (int(cx - lay.size[0] / 2), int(cy - lay.size[1] / 2)))


def rounded_box(w, h, fill, r=36, outline=None, ow=6):
    lay = Image.new("RGBA", (w, h))
    ImageDraw.Draw(lay).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill,
                                          outline=outline, width=ow)
    return lay


_cache = {}


def cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


# ---------- シーン描画 ----------
def current_line(sc, t):
    cur = None
    for ln in sc["lines"]:
        if t >= ln["start"] - 0.05:
            cur = ln
    return cur


def draw_caption(img, sc, t, y=1500):
    ln = current_line(sc, t)
    if not ln:
        return
    k = t - ln["start"]
    s = ease_out_back(k / 0.22, 2.2) if k < 0.3 else 1.0
    lay = cached(("cap", ln["cap"]), lambda: text_layer(ln["cap"], 74, stroke=12))
    # 帯
    band = cached(("band", lay.size[0]), lambda: rounded_box(min(W - 40, lay.size[0] + 40), 150,
                                                             (0, 0, 0, 120), r=30))
    paste_c(img, band, W / 2, y + 6, scale=min(1, 0.6 + 0.4 * s), alpha=clamp(k / 0.1))
    paste_c(img, lay, W / 2, y, scale=0.7 + 0.3 * s, alpha=clamp(k / 0.08))


def draw_header(img, t, active):
    # 上部: タイトルと進捗バー
    lay = cached("hdr", lambda: text_layer("今日からできる 金持ち習慣5選", 46, fill=GOLD,
                                           stroke=6, fpath=F_ROUND))
    paste_c(img, lay, W / 2, 170)
    d = ImageDraw.Draw(img)
    sw, gap, x0, y0 = 170, 14, (W - (170 * 5 + 14 * 4)) / 2, 230
    for i in range(5):
        x = x0 + i * (sw + gap)
        d.rounded_rectangle([x, y0, x + sw, y0 + 16], 8, fill=(255, 255, 255, 50))
        fill_ratio = 1.0 if i + 1 < active else (clamp(t) if i + 1 == active else 0)
        if fill_ratio > 0:
            d.rounded_rectangle([x, y0, x + sw * fill_ratio, y0 + 16], 8, fill=GOLD)


def scene_hook(img, sc, t):
    L = sc["lines"]
    shake = 0
    t1 = L[0]["start"]; t2 = L[1]["start"]; t3 = L[2]["start"]
    for ts in (t1, t2):
        k = t - ts
        if 0 <= k < 0.25:
            shake = (1 - k / 0.25) * 22
    ox = rng.uniform(-shake, shake); oy = rng.uniform(-shake, shake)
    # 1行目
    k = t - t1
    if k >= -0.05:
        lay = cached("h1", lambda: text_layer("9割の人が知らない", 96, stroke=12))
        s = 2.4 - 1.4 * ease_out(k / 0.18)
        paste_c(img, lay, W / 2 + ox, 640 + oy, scale=s, alpha=clamp(k / 0.1))
        if k > 0.25:  # 赤いアンダーライン
            d = ImageDraw.Draw(img)
            ww = 760 * ease_out((k - 0.25) / 0.3)
            d.rounded_rectangle([W / 2 - 380 + ox, 715 + oy, W / 2 - 380 + ww + ox, 735 + oy], 10, fill=RED)
    # 2行目(メイン)
    k = t - t2
    if k >= -0.05:
        a = cached("h2a", lambda: text_layer("金持ちになる", 150, stroke=14,
                                             grad=((255, 236, 150), GOLD2)))
        b = cached("h2b", lambda: text_layer("習慣5選", 230, stroke=16,
                                             grad=((255, 236, 150), GOLD2)))
        s = 2.6 - 1.6 * ease_out(k / 0.18)
        # 後光
        glow = cached("glow", lambda: Image.new("RGBA", (900, 900)))
        if "glowdone" not in _cache:
            gd = ImageDraw.Draw(glow)
            for r in range(450, 0, -10):
                gd.ellipse([450 - r, 450 - r, 450 + r, 450 + r],
                           fill=(255, 190, 60, int(3 + 40 * (1 - r / 450) ** 2)))
            _cache["glowdone"] = 1
        rot = (t * 20) % 360
        rays = cached("rays", make_rays)
        paste_c(img, rays, W / 2, 1010, scale=1.0, alpha=clamp(k / 0.3) * 0.5, rot=rot)
        paste_c(img, glow, W / 2, 1010, alpha=clamp(k / 0.3))
        paste_c(img, a, W / 2 + ox, 880 + oy, scale=s, alpha=clamp(k / 0.1))
        paste_c(img, b, W / 2 + ox, 1090 + oy, scale=s * (1 + 0.03 * math.sin(t * 8)), alpha=clamp(k / 0.1))
        # フラッシュ
        if 0 <= k < 0.15:
            fl = Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - k / 0.15))))
            img.alpha_composite(fl)
    # 3行目 + 5つの絵文字ティザー
    k = t - t3
    if k >= 0:
        for i in range(5):
            kk = k - i * 0.08
            e = cached(("em", i + 1, 120), lambda i=i: emoji_layer(EMOJI[i + 1], 120))
            paste_c(img, e, 180 + i * 180, 1330 + math.sin(t * 4 + i) * 10,
                    scale=ease_out_back(kk / 0.3), alpha=clamp(kk / 0.1))
    draw_caption(img, sc, t, y=1560) if k >= 0 else None


def make_rays():
    lay = Image.new("RGBA", (1600, 1600))
    d = ImageDraw.Draw(lay)
    for i in range(16):
        a0 = i * 2 * math.pi / 16
        a1 = a0 + math.pi / 32
        d.polygon([(800, 800), (800 + 1100 * math.cos(a0), 800 + 1100 * math.sin(a0)),
                   (800 + 1100 * math.cos(a1), 800 + 1100 * math.sin(a1))],
                  fill=(255, 200, 80, 40))
    return lay.filter(ImageFilter.GaussianBlur(6))


def scene_habit(img, sc, t):
    n = sc["num"]
    k = t - sc["start"]
    progress = (t - sc["start"]) / (sc["end"] - sc["start"])
    draw_header(img, progress, n)
    # 番号サークル
    circ = cached("circle", lambda: make_circle())
    s = ease_out_back(k / 0.35, 2.0)
    paste_c(img, circ, W / 2, 520, scale=s * (1 + 0.02 * math.sin(t * 6)), rot=(1 - clamp(k / 0.35)) * 90)
    num = cached(("num", n), lambda: text_layer(f"{n}", 230, fill=INK, stroke=0, shadow=False))
    paste_c(img, num, W / 2, 505, scale=s)
    lbl = cached("lbl", lambda: text_layer("HABIT", 40, fill=GOLD, stroke=0, fpath=F_ROUND, shadow=False))
    paste_c(img, lbl, W / 2, 340, alpha=clamp((k - 0.2) / 0.2))
    # 絵文字
    e = cached(("em", n, 170), lambda: emoji_layer(EMOJI[n], 170))
    ke = k - 0.35
    paste_c(img, e, W / 2 + 250, 420 + math.sin(t * 3) * 14, scale=ease_out_back(ke / 0.35),
            rot=math.sin(t * 2) * 8)
    # タイトル(左からスライド)
    kt = k - 0.3
    title = cached(("title", n), lambda: text_layer(sc["title"], 120, stroke=14,
                                                    grad=((255, 240, 170), GOLD2)))
    x = W / 2 - (1 - ease_out(kt / 0.35)) * 900
    paste_c(img, title, x, 820, alpha=clamp(kt / 0.15))
    # 詳細ボックス
    kb = k - 0.7
    if kb > 0:
        box = cached(("box", n), lambda: make_subbox(sc["sub"]))
        paste_c(img, box, W / 2, 1060, scale=0.9 + 0.1 * ease_out_back(kb / 0.3), alpha=clamp(kb / 0.2))
    draw_caption(img, sc, t)
    if n == 5:
        disc = cached("disc", lambda: make_disc())
        paste_c(img, disc, W / 2, 1800)


def make_disc():
    a, b = DISCLAIMER.split("。", 1)
    l1 = text_layer(a + "。", 30, fill=(205, 205, 215), stroke=0, fpath=F_ROUND, shadow=False)
    l2 = text_layer(b, 30, fill=(205, 205, 215), stroke=0, fpath=F_ROUND, shadow=False)
    lay = Image.new("RGBA", (max(l1.size[0], l2.size[0]), l1.size[1] + l2.size[1] - 20))
    lay.alpha_composite(l1, ((lay.size[0] - l1.size[0]) // 2, 0))
    lay.alpha_composite(l2, ((lay.size[0] - l2.size[0]) // 2, l1.size[1] - 20))
    return lay


def make_circle():
    lay = Image.new("RGBA", (340, 340))
    d = ImageDraw.Draw(lay)
    for r in range(170, 140, -2):
        d.ellipse([170 - r, 170 - r, 170 + r, 170 + r], fill=(255, 200, 60, int(255 * (1 - (r - 140) / 30) ** 2 * 0.5)))
    d.ellipse([30, 30, 310, 310], fill=GOLD, outline=(255, 240, 180), width=8)
    d.ellipse([50, 50, 290, 290], outline=GOLD2, width=4)
    return lay


def make_subbox(txt):
    t = text_layer(txt, 52, stroke=0, fpath=F_ROUND, shadow=False, maxw=W - 200)
    box = rounded_box(t.size[0] + 80, t.size[1] + 60, (255, 255, 255, 28), r=34,
                      outline=(255, 200, 60, 200), ow=5)
    box.alpha_composite(t, (40, 30))
    # チェックマーク
    return box


RECAP = ["先取り貯蓄", "支出を記録", "24時間ルール", "毎日15分の自己投資", "新NISAで積立"]


def scene_outro(img, sc, t):
    k = t - sc["start"]
    draw_header(img, 1, 6)
    L = sc["lines"]
    head = cached("ohead", lambda: text_layer("まとめ", 110, stroke=12, grad=((255, 240, 170), GOLD2)))
    paste_c(img, head, W / 2, 400, scale=ease_out_back(k / 0.3))
    t_hl = L[1]["start"]
    for i, item in enumerate(RECAP):
        ki = k - 0.15 - i * 0.12
        hl = (i in (0, 4)) and t >= t_hl
        lay = cached(("rc", i, hl), lambda i=i, item=item, hl=hl: make_recap(i, item, hl))
        x = W / 2 + (1 - ease_out(ki / 0.3)) * W
        pulse = 1 + (0.04 * math.sin((t - t_hl) * 10) if hl else 0)
        paste_c(img, lay, x, 560 + i * 140, scale=pulse, alpha=clamp(ki / 0.15))
    # 最後: 保存CTA
    kc = t - L[3]["start"]
    if kc > 0:
        cta = cached("cta", make_cta)
        paste_c(img, cta, W / 2, 1300 + math.sin(t * 6) * 8, scale=ease_out_back(kc / 0.35))
        hand = cached("hand", lambda: emoji_layer("👆", 120))
        paste_c(img, hand, W / 2 + 330, 1420 - abs(math.sin(t * 5)) * 30, alpha=clamp(kc / 0.2))
    draw_caption(img, sc, t, y=1560)
    disc = cached("disc", lambda: make_disc())
    paste_c(img, disc, W / 2, 1800)


def make_recap(i, item, hl):
    w, h = 820, 116
    box = rounded_box(w, h, (255, 200, 60, 70) if hl else (255, 255, 255, 22), r=28,
                      outline=GOLD if hl else (255, 255, 255, 60), ow=5 if hl else 2)
    d = ImageDraw.Draw(box)
    d.ellipse([22, 18, 102, 98], fill=GOLD if hl else (255, 255, 255, 60))
    nf = font(F_BLACK, 52)
    d.text((62, 56), str(i + 1), font=nf, fill=INK, anchor="mm")
    tf = font(F_ROUND, 54)
    d.text((132, 58), item, font=tf, fill=WHITE, anchor="lm")
    if hl:
        d.text((w - 40, 58), "自動化!", font=font(F_BLACK, 40), fill=GOLD, anchor="rm")
    return box


def make_cta():
    t = text_layer("保存して今日ひとつ始めよう", 64, fill=INK, stroke=0, shadow=False)
    box = rounded_box(t.size[0] + 100, t.size[1] + 70, GOLD, r=60, outline=(255, 245, 200), ow=6)
    box.alpha_composite(t, (50, 35))
    return box


# ---------- メインループ ----------
def frame(t):
    img = BG.copy()
    draw_candles(img, t)
    sc = SC[0]
    for s in SC:
        if t >= s["start"] - 0.3:
            sc = s
    draw_particles(img, t, boost=2.0 if sc["kind"] == "hook" else 1.0)
    # シーン切り替え: ズームイン+白ワイプ
    if sc["kind"] == "hook":
        scene_hook(img, sc, t)
    elif sc["kind"] == "habit":
        scene_habit(img, sc, t)
    else:
        scene_outro(img, sc, t)
    k = t - (sc["start"] - 0.3)
    if sc["kind"] != "hook" and 0 <= k < 0.3:
        # ワイプ(金色の斜め帯が横切る)
        lay = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(lay)
        x = -W * 0.6 + (k / 0.3) * W * 2.2
        d.polygon([(x, 0), (x + 500, 0), (x + 200, H), (x - 300, H)], fill=(255, 200, 60, 230))
        img.alpha_composite(lay)
    return img.convert("RGB")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for ts in map(float, sys.argv[2:]):
            frame(ts).save(f"build/prev_{ts:05.2f}.png")
        sys.exit()
    # 並列: 引数 part i/n
    i, n = map(int, sys.argv[1].split("/"))
    nf = int(TOTAL * FPS)
    a, b = nf * i // n, nf * (i + 1) // n
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                           "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                           f"build/part{i}.mp4"], stdin=subprocess.PIPE)
    for f in range(a, b):
        ff.stdin.write(frame(f / FPS).tobytes())
    ff.stdin.close(); ff.wait()
