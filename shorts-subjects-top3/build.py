#!/usr/bin/env python3
"""ショート動画「あらゆる仕事で役立つ科目 TOP3」ビルドスクリプト

使い方:
  python3 build.py
    voice/ に VOICEVOX の音声 (01.wav〜08.wav, 四国めたん) があれば、それに合わせて
    尺を決めてナレーションを合成します。なければ推定尺で、ナレーションなしの版を作ります。

  出力: out/short.mp4 (1080x1920, 30fps)
"""
import glob
import math
import os
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 44100
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

# ---------------------------------------------------------------- 台本
SCENES = [
    dict(id="hook", color=((255, 94, 98), (255, 153, 102)),
         text="学生時代の勉強、将来ほんとに役立つのはどれ？あらゆる仕事で使える科目トップ3、発表します！"),
    dict(id="math", color=((60, 60, 80), (110, 110, 140)),
         text="ちなみに数学は、まさかのランク外！"),
    dict(id="rank", rank=3, subj="英語", color=((54, 120, 255), (0, 210, 255)),
         text="第3位、英語！外国人のお客さん対応や英語での情報収集、転職や昇進でも評価されます。",
         points=[("外国人のお客さん対応", "外国人"), ("英語で情報収集", "情報収集"), ("転職・昇進で評価", "転職")]),
    dict(id="rank", rank=2, subj="情報", color=((0, 180, 120), (140, 230, 80)),
         text="第2位、情報！今はどんな職場でもパソコンやAIを使います。使いこなせるかどうかで、仕事の効率に大きな差が出ます。",
         points=[("どの職場でもPC・スマホ", "どんな職場"), ("AIツールの活用", "AI"), ("作業効率に大差", "使いこなせる")]),
    dict(id="drum", color=((20, 10, 40), (60, 20, 90)),
         text="そして、栄えある第1位は…"),
    dict(id="rank", rank=1, subj="国語", color=((255, 170, 0), (255, 90, 40)),
         text="国語！指示を理解する、報告する、文章を書く。どんな仕事でも必ず使う、最強の科目です。",
         points=[("指示を正しく理解", "指示"), ("報告・相談・説明", "報告"), ("伝わる文章を書く", "文章")]),
    dict(id="extra", subj="公民", color=((150, 80, 220), (230, 110, 200)),
         text="次点は公民。税金や契約、働く人の権利は、全員に関わる知識です。",
         points=[("税金・社会保険", "税金"), ("契約のルール", "契約"), ("働く人の権利", "権利")]),
    dict(id="cta", color=((255, 94, 98), (255, 153, 102)),
         text="あなたが役に立ったと思う科目は？コメントで教えてね！"),
]
PRE = 0.15
POST = {"hook": 0.3, "math": 0.5, "rank": 0.6, "drum": 1.6, "extra": 0.5, "cta": 2.0}


# ---------------------------------------------------------------- 音声読み込み
def read_wav(path):
    with wave.open(path) as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    a = np.frombuffer(raw, dtype={2: np.int16, 4: np.int32}[sw]).astype(np.float32)
    a /= float(2 ** (8 * sw - 1))
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        n = int(len(a) * SR / sr)
        a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
    return a


def load_voices():
    files = sorted(glob.glob(os.path.join(HERE, "voice", "*.wav")))
    if len(files) != len(SCENES):
        if files:
            print(f"voice/ の wav が {len(files)} 個です（{len(SCENES)} 個必要）。ナレーションなしで作ります。")
        return None
    return [read_wav(f) for f in files]


# ---------------------------------------------------------------- タイムライン
def build_timeline(voices):
    t = 0.0
    for i, s in enumerate(SCENES):
        if voices:
            vd = len(voices[i]) / SR
        else:
            vd = 0.4 + 0.125 * len(s["text"])  # 推定（四国めたん 標準速度）
        s["vstart"] = t + PRE
        s["vdur"] = vd
        s["start"] = t
        s["dur"] = PRE + vd + POST[s["id"]]
        t += s["dur"]
    return t


def char_time(s, sub):
    """台本中の文字位置からおおよその発話時刻（シーン内ローカル）を求める"""
    idx = s["text"].find(sub)
    idx = max(idx, 0)
    return PRE + s["vdur"] * idx / len(s["text"])


# ---------------------------------------------------------------- 描画ヘルパー
_font_cache, _sprite_cache = {}, {}


def font(size):
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(FONT, size)
    return _font_cache[size]


def sprite(text, size, fill=(255, 255, 255), stroke=0, stroke_fill=(0, 0, 0), shadow=True):
    key = (text, size, fill, stroke, stroke_fill, shadow)
    if key in _sprite_cache:
        return _sprite_cache[key]
    f = font(size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    pad = stroke + 14
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        d.text((pad - l + 8, pad - t + 10), text, font=f, fill=(0, 0, 0, 110),
               stroke_width=stroke, stroke_fill=(0, 0, 0, 110))
    d.text((pad - l, pad - t), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    _sprite_cache[key] = im
    return im


def paste_center(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, resample=Image.BILINEAR, expand=True)
    if alpha < 1.0:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out_back(x):
    x = clamp01(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


_bg_cache = {}


def background(colors, t, dark=False):
    """斜めストライプが流れるグラデーション背景"""
    if colors not in _bg_cache:
        c1, c2 = np.array(colors[0], np.float32), np.array(colors[1], np.float32)
        yy, xx = np.mgrid[0:H + 200, 0:W + 200].astype(np.float32)
        g = ((yy / (H + 200)) * 0.7 + (xx / (W + 200)) * 0.3)[..., None]
        img = c1 * (1 - g) + c2 * g
        stripe = (((xx + yy) // 90) % 2 == 0)[..., None]
        img = np.where(stripe, img * 1.07, img * 0.95)
        _bg_cache[colors] = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    off = int((t * 60) % 180)
    return _bg_cache[colors].crop((off, off, off + W, off + H))


def rays(canvas, cx, cy, t, color=(255, 255, 255, 40), n=16):
    d = ImageDraw.Draw(canvas)
    R = 1600
    for i in range(n):
        a0 = t * 0.6 + i * 2 * math.pi / n
        a1 = a0 + math.pi / n * 0.6
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)),
                   (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=color)


CONFETTI = [(random.Random(i).uniform(0, W), random.Random(i + 99).uniform(-400, 0),
             random.Random(i + 7).uniform(250, 600), random.Random(i + 3).uniform(-150, 150),
             random.Random(i + 5).choice([(255, 80, 80), (255, 210, 0), (80, 200, 255), (120, 255, 120),
                                          (255, 120, 220), (255, 255, 255)]),
             random.Random(i + 11).uniform(0, 6.28)) for i in range(140)]


def confetti(canvas, t):
    d = ImageDraw.Draw(canvas)
    for x0, y0, vy, vx, col, ph in CONFETTI:
        y = y0 + vy * t + 120 * t * t
        x = x0 + vx * t + 40 * math.sin(t * 4 + ph)
        if y > H + 40:
            continue
        w = 14 + 10 * abs(math.sin(t * 6 + ph))
        d.rectangle([x, y, x + w, y + 22], fill=col)


def wrap(text, maxchars):
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= maxchars and ch not in "、。！？…":
            lines.append(cur)
            cur = ""
    if cur:
        # 句読点だけが行頭に来ないように
        if lines and (len(cur) <= 2 or all(c in "、。！？…" for c in cur)):
            lines[-1] += cur
        else:
            lines.append(cur)
    return lines


def subtitle_chunks(s):
    """台本を句読点で区切って字幕チャンクに分け、文字数比で時刻を割り当てる"""
    chunks, cur = [], ""
    for ch in s["text"]:
        cur += ch
        if ch in "。！？" or (ch == "、" and len(cur) >= 12):
            chunks.append(cur)
            cur = ""
    if cur:
        chunks.append(cur)
    out, pos, n = [], 0, len(s["text"])
    for c in chunks:
        t0 = PRE + s["vdur"] * pos / n
        pos += len(c)
        t1 = PRE + s["vdur"] * pos / n
        out.append((t0, t1, c))
    return out


def draw_subtitle(canvas, s, lt):
    chunks = subtitle_chunks(s)
    cur = None
    for t0, t1, c in chunks:
        if t0 - 0.05 <= lt:
            cur = (t0, c)
    if cur is None or lt > PRE + s["vdur"] + 0.4:
        return
    t0, c = cur
    lines = wrap(c, 12)
    k = ease_out_back((lt - t0) / 0.18)
    y = 1560
    d = ImageDraw.Draw(canvas)
    box_h = 92 * len(lines) + 40
    d.rounded_rectangle([60, y - 20, W - 60, y - 20 + box_h], 30, fill=(0, 0, 0, 150))
    for i, ln in enumerate(lines):
        sp = sprite(ln, 70, fill=(255, 255, 255), stroke=5, stroke_fill=(20, 20, 20), shadow=False)
        paste_center(canvas, sp, W / 2, y + 26 + i * 92, scale=0.9 + 0.1 * k)


# ---------------------------------------------------------------- シーン描画
def draw_header(canvas, gt):
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 70, W, 200], fill=(0, 0, 0, 120))
    a = sprite("あらゆる仕事で役立つ科目", 62, fill=(255, 255, 255), stroke=4, stroke_fill=(0, 0, 0), shadow=False)
    b = sprite("TOP3", 80, fill=(255, 225, 0), stroke=6, stroke_fill=(180, 0, 0), shadow=False)
    x0 = (W - a.width - b.width + 10) / 2
    paste_center(canvas, a, x0 + a.width / 2, 135)
    pulse = 1 + 0.05 * math.sin(gt * 8)
    paste_center(canvas, b, x0 + a.width - 10 + b.width / 2, 135, scale=pulse)


def scene_hook(c, s, lt, gt):
    rays(c, W / 2, 900, gt)
    lines = [("学生時代の勉強", 0.0, 96, (255, 255, 255)),
             ("将来ほんとに", char_time(s, "将来") - 0.1, 110, (255, 255, 255)),
             ("役立つのはどれ？", char_time(s, "役立つ") - 0.1, 120, (255, 240, 0))]
    for i, (txt, t0, size, col) in enumerate(lines):
        k = ease_out_back((lt - t0) / 0.3)
        paste_center(c, sprite(txt, size, fill=col, stroke=8), W / 2, 450 + i * 170, scale=k)
    t_top = char_time(s, "トップ3") - 0.15
    if lt > t_top:
        k = ease_out_back((lt - t_top) / 0.35)
        wob = math.sin((lt - t_top) * 10) * 3 * max(0, 1 - (lt - t_top))
        paste_center(c, sprite("TOP3", 330, fill=(255, 225, 0), stroke=16, stroke_fill=(200, 20, 20)),
                     W / 2, 1100, scale=k * (1 + 0.04 * math.sin(gt * 9)), rot=wob)
        paste_center(c, sprite("全職種で使える!!", 84, fill=(255, 255, 255), stroke=7), W / 2, 1340,
                     scale=ease_out_back((lt - t_top - 0.3) / 0.3))


def scene_math(c, s, lt, gt):
    draw_header(c, gt)
    k = ease_out_back(lt / 0.3)
    paste_center(c, sprite("数学", 300, fill=(255, 255, 255), stroke=14, stroke_fill=(40, 40, 60)),
                 W / 2, 820, scale=k)
    tx = char_time(s, "まさか") - 0.05
    if lt > tx:
        p = ease_out((lt - tx) / 0.15)
        sc = 1.8 - 0.8 * p
        d = ImageDraw.Draw(c)
        L = 300 * sc
        for sgn in (1, -1):
            d.line([(W / 2 - L, 820 - L * sgn), (W / 2 + L, 820 + L * sgn)], fill=(255, 40, 60, 230),
                   width=int(55 * sc))
        paste_center(c, sprite("まさかのランク外!?", 110, fill=(255, 230, 0), stroke=9, stroke_fill=(150, 0, 0)),
                     W / 2, 1250, scale=ease_out_back((lt - tx - 0.1) / 0.3))


MEDAL = {3: ((205, 127, 50), "銅"), 2: ((200, 205, 215), "銀"), 1: ((255, 215, 0), "金")}


def scene_rank(c, s, lt, gt, extra=False):
    draw_header(c, gt)
    rank = s.get("rank")
    t_subj = PRE if s["text"].startswith(s["subj"]) else char_time(s, s["subj"]) - 0.08
    if rank == 1:
        rays(c, W / 2, 700, gt, color=(255, 255, 200, 55), n=20)
    # 順位バッジ
    if extra:
        badge, bcol, bstroke = "次点", (255, 255, 255), (90, 30, 140)
    else:
        badge, bcol, bstroke = f"第{rank}位", MEDAL[rank][0], (60, 30, 0)
    k = ease_out_back(lt / 0.3)
    paste_center(c, sprite(badge, 150, fill=bcol, stroke=10, stroke_fill=bstroke), W / 2, 380, scale=k)
    # 科目名（ドンと落ちてくる）
    if lt > t_subj:
        p = (lt - t_subj) / 0.22
        sc = 2.6 - 1.6 * ease_out(p) if p < 1 else 1 + 0.03 * math.sin(gt * 7)
        size = 300 if rank == 1 else 260
        col = (255, 240, 0) if rank == 1 else (255, 255, 255)
        paste_center(c, sprite(s["subj"], size, fill=col, stroke=16, stroke_fill=(30, 30, 30)),
                     W / 2, 720, scale=sc, alpha=clamp01(p * 3))
    # ポイント
    for i, (txt, key) in enumerate(s["points"]):
        t0 = char_time(s, key) - 0.15
        if lt < t0:
            continue
        p = ease_out((lt - t0) / 0.3)
        x = W / 2 + (1 - p) * 700
        y = 1010 + i * 150
        d = ImageDraw.Draw(c)
        d.rounded_rectangle([x - 440, y - 60, x + 440, y + 60], 60, fill=(255, 255, 255, 235))
        d.ellipse([x - 420, y - 42, x - 336, y + 42], fill=(255, 80, 80))
        paste_center(c, sprite(str(i + 1), 60, fill=(255, 255, 255), shadow=False), x - 378, y)
        sp = sprite(txt, 62, fill=(30, 30, 40), shadow=False)
        paste_center(c, sp, x - 300 + sp.width / 2, y)
    if rank == 1 and lt > t_subj:
        confetti(c, lt - t_subj)


def scene_drum(c, s, lt, gt):
    draw_header(c, gt)
    k = ease_out_back(lt / 0.3)
    paste_center(c, sprite("栄えある", 110, fill=(255, 255, 255), stroke=8), W / 2, 560, scale=k)
    paste_center(c, sprite("第1位は…", 180, fill=(255, 215, 0), stroke=12, stroke_fill=(80, 40, 0)),
                 W / 2, 780, scale=k)
    t_q = PRE + s["vdur"]
    if lt > t_q - 0.3:
        q = lt - (t_q - 0.3)
        pulse = 1 + 0.12 * abs(math.sin(q * (6 + q * 10)))
        paste_center(c, sprite("？", 420, fill=(255, 255, 255), stroke=16, stroke_fill=(120, 0, 160)),
                     W / 2, 1180, scale=pulse * ease_out_back(q / 0.3))


def scene_cta(c, s, lt, gt):
    rays(c, W / 2, 900, gt)
    k = ease_out_back(lt / 0.3)
    paste_center(c, sprite("あなたが役立ったと", 100, fill=(255, 255, 255), stroke=8), W / 2, 470, scale=k)
    paste_center(c, sprite("思う科目は？", 130, fill=(255, 240, 0), stroke=10), W / 2, 640, scale=k)
    rows = [("1位", "国語", (255, 215, 0)), ("2位", "情報", (200, 205, 215)), ("3位", "英語", (205, 127, 50))]
    for i, (r, sub, col) in enumerate(rows):
        p = ease_out_back((lt - 0.4 - i * 0.15) / 0.3)
        paste_center(c, sprite(f"{r}  {sub}", 96, fill=col, stroke=8, stroke_fill=(40, 20, 0)),
                     W / 2, 850 + i * 125, scale=p)
    t_c = char_time(s, "コメント") - 0.1
    if lt > t_c:
        p = ease_out_back((lt - t_c) / 0.3)
        bob = 18 * math.sin(gt * 8)
        d = ImageDraw.Draw(c)
        d.rounded_rectangle([140, 1215, W - 140, 1375], 80, fill=(255, 50, 80, 240))
        paste_center(c, sprite("コメントで教えてね", 82, fill=(255, 255, 255), stroke=0), W / 2, 1295, scale=p)
        ax, ay = W / 2, 1450 + bob
        d.polygon([(ax - 50, ay - 30), (ax + 50, ay - 30), (ax, ay + 30)], fill=(255, 255, 255, 230))


def render_frame(t, total):
    s = next((x for x in SCENES if x["start"] <= t < x["start"] + x["dur"]), SCENES[-1])
    lt = t - s["start"]
    c = background(s["color"], t).copy()
    sid = s["id"]
    if sid == "hook":
        scene_hook(c, s, lt, t)
    elif sid == "math":
        scene_math(c, s, lt, t)
    elif sid == "rank":
        scene_rank(c, s, lt, t)
    elif sid == "extra":
        scene_rank(c, s, lt, t, extra=True)
    elif sid == "drum":
        scene_drum(c, s, lt, t)
    elif sid == "cta":
        scene_cta(c, s, lt, t)
    draw_subtitle(c, s, lt)
    d = ImageDraw.Draw(c)
    # 進行バー
    d.rectangle([0, 0, W, 14], fill=(0, 0, 0, 120))
    d.rectangle([0, 0, int(W * t / total), 14], fill=(255, 230, 0))
    # クレジット（VOICEVOX 利用規約による表記）
    d.rounded_rectangle([W - 370, H - 88, W - 30, H - 32], 20, fill=(0, 0, 0, 140))
    paste_center(c, sprite("VOICEVOX:四国めたん", 34, fill=(255, 255, 255), shadow=False), W - 200, H - 60,
                 alpha=0.85)
    # 切り替え時の白フラッシュ＆揺れ
    shake = 0.0
    if lt < 0.12 and sid != "hook":
        c = Image.blend(c, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.8 * (1 - lt / 0.12))
    if sid in ("rank", "extra"):
        t_subj = PRE if s["text"].startswith(s["subj"]) else char_time(s, s["subj"]) - 0.08
        dt = lt - t_subj - 0.22
        if 0 <= dt < 0.35:
            shake = 26 * (1 - dt / 0.35) * (1.6 if s.get("rank") == 1 else 1)
    if sid == "math":
        dt = lt - char_time(s, "まさか") + 0.05 - 0.15
        if 0 <= dt < 0.3:
            shake = 20 * (1 - dt / 0.3)
    img = c.convert("RGB")
    if shake:
        dx, dy = int(shake * math.sin(t * 90)), int(shake * math.cos(t * 77))
        bg = Image.new("RGB", (W, H), (0, 0, 0))
        bg.paste(img, (dx, dy))
        img = bg
    return img


# ---------------------------------------------------------------- 音（BGM・効果音）
def lowpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x)).astype(np.float32)


def highpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (cutoff / np.maximum(f, 1)) ** 4)
    return np.fft.irfft(X, len(x)).astype(np.float32)


def add(buf, snd, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    n = min(len(snd), len(buf) - i)
    buf[i:i + n] += snd[:n] * gain


def env(n, decay):
    return np.exp(-np.arange(n) / SR / decay).astype(np.float32)


rng = np.random.default_rng(1)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.12)).astype(np.float32)


def clap():
    n = int(0.25 * SR)
    return highpass(rng.standard_normal(n).astype(np.float32), 1200) * env(n, 0.06) * 0.6


def hat():
    n = int(0.06 * SR)
    return highpass(rng.standard_normal(n).astype(np.float32), 7000) * env(n, 0.015) * 0.5


def tone(freq, dur, kind="saw", decay=None):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "saw":
        y = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 9))
    elif kind == "square":
        y = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 12, 2))
    else:
        y = np.sin(2 * np.pi * freq * t)
    e = env(n, decay) if decay else np.ones(n, np.float32)
    a = min(n, int(0.005 * SR))
    e[:a] *= np.linspace(0, 1, a)
    e[-a:] *= np.linspace(1, 0, a)
    return (y * e).astype(np.float32)


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def make_bgm(total, drum_scene, r1_start):
    bpm = 128
    beat = 60 / bpm
    buf_drums = np.zeros(int(total * SR) + SR, np.float32)
    buf_bass = np.zeros_like(buf_drums)
    buf_arp = np.zeros_like(buf_drums)
    buf_pad = np.zeros_like(buf_drums)
    K, C, Hh = kick(), clap(), hat()
    # Am - F - C - G
    prog = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [64, 67, 72]), (55, [67, 71, 74])]
    drop0, drop1 = drum_scene["start"], r1_start
    nbeats = int(total / beat) + 1
    for b in range(nbeats):
        t = b * beat
        if drop0 <= t < drop1:
            continue  # ドラムロール中は BGM を止めて緊張感を出す
        bar = (b // 4) % 4
        root, chord = prog[bar]
        add(buf_drums, K, t, 0.9)
        if b % 2 == 1:
            add(buf_drums, C, t, 0.5)
        add(buf_drums, Hh, t + beat / 2, 0.35)
        add(buf_drums, Hh, t + beat / 4 * 3, 0.15)
        for e in range(2):
            add(buf_bass, tone(midi(root - 12 + (12 if e else 0)), beat / 2 * 0.9, "saw", 0.15),
                t + e * beat / 2, 0.30)
        for e in range(4):
            note = chord[(b * 4 + e) % 3] + (12 if (b * 4 + e) % 6 >= 3 else 0)
            add(buf_arp, tone(midi(note), beat / 4 * 0.9, "square", 0.06), t + e * beat / 4, 0.10)
        if b % 4 == 0:
            for n in chord:
                add(buf_pad, tone(midi(n - 12), beat * 4, "saw") * 0.5, t, 0.05)
    bgm = buf_drums + lowpass(buf_bass, 900) + lowpass(buf_arp, 3500) + lowpass(buf_pad, 1500)
    return bgm


def make_sfx(total):
    buf = np.zeros(int(total * SR) + SR, np.float32)

    def whoosh():
        n = int(0.4 * SR)
        x = rng.standard_normal(n).astype(np.float32)
        x = highpass(lowpass(x, 3000), 400)
        e = np.sin(np.linspace(0, np.pi, n)) ** 2
        return x * e * 0.5

    def impact():
        n = int(0.9 * SR)
        t = np.arange(n) / SR
        boom = np.sin(2 * np.pi * np.cumsum(40 + 80 * np.exp(-t / 0.08)) / SR) * env(n, 0.3)
        noise = lowpass(rng.standard_normal(n).astype(np.float32), 2500) * env(n, 0.08)
        return (boom * 0.9 + noise * 0.5).astype(np.float32)

    def ding(f=1568):
        return tone(f, 0.5, "sine", 0.12) * 0.5 + tone(f * 2, 0.5, "sine", 0.06) * 0.2

    def buzzer():
        return lowpass(tone(110, 0.55, "square"), 1800) * 0.35

    def crash():
        n = int(2.5 * SR)
        return highpass(rng.standard_normal(n).astype(np.float32), 4000) * env(n, 0.6) * 0.5

    def drumroll(dur):
        out = np.zeros(int(dur * SR), np.float32)
        t = 0.0
        snare = highpass(rng.standard_normal(int(0.08 * SR)).astype(np.float32), 800) * env(int(0.08 * SR), 0.03)
        while t < dur:
            prog = t / dur
            add(out, snare, t, 0.25 + 0.5 * prog)
            t += 0.07 - 0.04 * prog
        return out

    def riser(dur):
        n = int(dur * SR)
        t = np.arange(n) / SR
        f = 200 + 1200 * (t / dur) ** 2
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) ** 2
        return (y * 0.18).astype(np.float32)

    for s in SCENES:
        st = s["start"]
        if s["id"] != "hook":
            add(buf, whoosh(), st - 0.2, 0.8)
        if s["id"] == "hook":
            add(buf, impact(), 0.0, 0.7)
            add(buf, impact(), st + char_time(s, "トップ3") - 0.15, 0.9)
        elif s["id"] == "math":
            add(buf, buzzer(), st + char_time(s, "まさか") + 0.1, 1.0)
        elif s["id"] in ("rank", "extra"):
            t_subj = PRE if s["text"].startswith(s["subj"]) else char_time(s, s["subj"]) - 0.08
            add(buf, impact(), st + t_subj + 0.2, 1.0)
            if s.get("rank") == 1:
                add(buf, crash(), st + t_subj + 0.2, 1.0)
            for _, key in s["points"]:
                add(buf, ding(), st + char_time(s, key) - 0.15, 0.6)
        elif s["id"] == "drum":
            add(buf, drumroll(s["dur"]), st, 1.0)
            add(buf, riser(s["dur"]), st, 1.0)
        elif s["id"] == "cta":
            add(buf, ding(1318), st + char_time(s, "コメント") - 0.1, 0.7)
    return buf


def make_audio(total, voices, path):
    n = int(total * SR)
    drum = next(s for s in SCENES if s["id"] == "drum")
    r1 = next(s for s in SCENES if s.get("rank") == 1)
    bgm = make_bgm(total, drum, r1["start"] + PRE)[:n]
    sfx = make_sfx(total)[:n]
    voice = np.zeros(n, np.float32)
    if voices:
        for s, v in zip(SCENES, voices):
            add(voice, v, s["vstart"], 1.0)
    # ナレーション中は BGM を下げる（ダッキング）
    vol = np.abs(voice)
    k = int(0.15 * SR)
    sm = np.convolve(vol, np.ones(k) / k, mode="same")
    duck = 1.0 - 0.55 * np.clip(sm * 30, 0, 1)
    bgm_gain = 0.42 if voices else 0.6
    fade = np.ones(n, np.float32)
    fl = int(1.2 * SR)
    fade[-fl:] = np.linspace(1, 0, fl)
    mix = bgm * bgm_gain * duck * fade + sfx * 0.55 + voice * 1.0
    mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- メイン
def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    voices = load_voices()
    total = build_timeline(voices)
    print(f"尺: {total:.1f} 秒 / ナレーション: {'あり' if voices else 'なし（推定尺）'}")
    audio = os.path.join(HERE, "out", "audio.wav")
    make_audio(total, voices, audio)
    out = os.path.join(HERE, "out", "short.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "24",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(total * FPS)
    for i in range(nf):
        p.stdin.write(render_frame(i / FPS, total).tobytes())
        if i % 150 == 0:
            print(f"  {i}/{nf} frames")
    p.stdin.close()
    p.wait()
    print("完成:", out)


if __name__ == "__main__":
    main()
