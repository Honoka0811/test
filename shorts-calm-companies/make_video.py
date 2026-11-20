"""穏やかな人が多いと言われる企業10選 — 縦型ショート動画を生成する（アニメーション版）。

必要なもの:
  - VOICEVOX ENGINE が localhost:50021 で起動していること
      docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
  - ffmpeg, Pillow, numpy
  - フォント M PLUS Rounded 1c（mplus800.ttf / mplus500.ttf を FONT_DIR に配置）

使い方: python3 make_video.py [FONT_DIR]
"""
import json
import math
import random
import subprocess
import sys
import urllib.parse
import urllib.request
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
FONT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "fonts"
ENGINE = "http://localhost:50021"
SPEAKER = 2  # 四国めたん（ノーマル）
SPEED = 1.2
W, H = 1080, 1920
FPS = 30
SR = 48000

BOLD = str(FONT_DIR / "mplus800.ttf")
MED = str(FONT_DIR / "mplus500.ttf")

BG_TOP = (226, 243, 233)
BG_BOTTOM = (252, 246, 234)
INK = (38, 54, 48)
SUB_INK = (70, 90, 82)
ACCENT = (62, 140, 110)
ACCENT_SOFT = (200, 228, 214)
METAN = (204, 74, 138)
YELLOW = (255, 214, 102)

LEAD = 0.35   # シーン開始からナレーション開始まで
TAIL = 0.45   # ナレーション終了からシーン終了まで
OUT_T = 0.28  # 退場アニメーションの長さ

COMPANIES = [
    ("三井不動産", "不動産", ["「人の三井」", "協調性を大切にする社風"],
     "まずは、三井不動産。「人の三井」と呼ばれ、協調性を大切にする社風ですわ。"),
    ("三井住友信託銀行", "信託銀行", ["メガバンクより落ち着いた", "真面目で温厚な雰囲気"],
     "三井住友信託銀行。メガバンクより落ち着いた、真面目で温厚な雰囲気ですの。"),
    ("味の素", "食品", ["人を大切にする社風", "働き方改革も進む"],
     "味の素。人を大切にする社風で、働き方改革も進んでいますわ。"),
    ("花王", "日用品", ["誠実で堅実", "チームワーク重視"],
     "花王。誠実で堅実、チームワークを重んじる会社ですわ。"),
    ("中外製薬", "製薬", ["落ち着いた製薬業界の中でも", "働きやすさの評価が高い"],
     "中外製薬。落ち着いた人が多い製薬業界でも、働きやすさの評価が高いんですの。"),
    ("NTTデータ", "IT・SIer", ["面倒見が良く", "温厚な人が多い"],
     "エヌティーティーデータ。面倒見が良く、温厚な人が多いと言われますわ。"),
    ("東京ガス", "インフラ", ["競争より協調", "安定志向の社風"],
     "東京ガス。インフラ企業らしく、競争より協調を重んじる雰囲気ですわ。"),
    ("日本郵船", "海運", ["品が良く", "穏やかな人が多い"],
     "にっぽんゆうせん。品が良く、穏やかな人が多いと評判ですの。"),
    ("キリンHD", "飲料", ["社員同士の仲が良く", "和やかな雰囲気"],
     "キリンホールディングス。社員同士の仲が良く、和やかな雰囲気ですわ。"),
    ("日本政策投資銀行", "政府系金融", ["ノルマの圧力が少なく", "知的で落ち着いた人が多い"],
     "にっぽん政策投資銀行。ノルマの圧力が少なく、知的で落ち着いた人が多いですわ。"),
]
INTRO_NARR = "穏やかな人が多いと言われる企業、10選をご紹介しますわ！"
OUTRO_NARR = ("ただし、雰囲気は部署や上司によって変わりますわ。"
              "口コミやオービー訪問で、ご自分の目で確かめてくださいましね。")
DISPLAY_FIX = {"エヌティーティーデータ": "NTTデータ", "にっぽんゆうせん": "日本郵船",
               "にっぽん政策投資銀行": "日本政策投資銀行", "オービー訪問": "OB訪問"}


# ============ 音声合成 ============
def tts(text):
    q = urllib.parse.urlencode({"text": text, "speaker": SPEAKER})
    req = urllib.request.Request(f"{ENGINE}/audio_query?{q}", method="POST")
    query = json.load(urllib.request.urlopen(req))
    query.update(speedScale=SPEED, prePhonemeLength=0.05, postPhonemeLength=0.1,
                 outputSamplingRate=SR, intonationScale=1.15)
    req = urllib.request.Request(f"{ENGINE}/synthesis?speaker={SPEAKER}",
                                 data=json.dumps(query).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    path = BUILD / "tmp.wav"
    path.write_bytes(urllib.request.urlopen(req).read())
    with wave.open(str(path)) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return data


# ============ 効果音・BGM ============
def env(n, attack=0.005, decay=0.1):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def se_pop():
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    f = 1100 * np.exp(-t * 12) + 380
    return 0.5 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.04)


def se_whoosh():
    n = int(SR * 0.3)
    rng = np.random.default_rng(1)
    noise = rng.standard_normal(n)
    # 簡易バンドパス（移動平均の差分）でシュッという音に
    k1, k2 = 3, 40
    lo = np.convolve(noise, np.ones(k1) / k1, "same") - np.convolve(noise, np.ones(k2) / k2, "same")
    t = np.arange(n) / SR
    shape = np.sin(np.pi * t / t[-1]) ** 2
    return 0.22 * lo * shape


def se_slam():
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    f = 160 * np.exp(-t * 6) + 50
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.18)
    click = np.random.default_rng(2).standard_normal(n) * env(n, 0.001, 0.01)
    return 0.7 * body + 0.15 * click


def se_chime():
    n = int(SR * 1.2)
    out = np.zeros(n)
    for i, f in enumerate([1046.5, 1318.5, 1568.0, 2093.0]):
        s = int(i * 0.08 * SR)
        m = n - s
        t = np.arange(m) / SR
        out[s:] += 0.18 * np.sin(2 * np.pi * f * t) * env(m, 0.003, 0.35)
    return out


def bgm(total_sec):
    """やさしいエレピ風の4和音ループ（C–G–Am–F、BPM 96）。"""
    n = int(SR * total_sec)
    out = np.zeros(n + SR * 8)
    beat = 60 / 96
    chords = [[60, 64, 67, 72], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]
    bass = [36, 43, 45, 41]
    arp = [0, 1, 2, 3, 2, 1, 2, 3]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)

    def note(midi, dur, vol, decay):
        m = int(SR * dur)
        t = np.arange(m) / SR
        f = hz(midi)
        tone = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
        return vol * tone * env(m, 0.004, decay)

    t0, bar = 0.0, 0
    while t0 < total_sec:
        ch = chords[bar % 4]
        b = note(bass[bar % 4], beat * 4, 0.16, 0.9)
        s = int(t0 * SR)
        out[s:s + len(b)] += b
        for i, a in enumerate(arp):
            nn = note(ch[a] + 12, beat * 1.5, 0.07, 0.35)
            s = int((t0 + i * beat / 2) * SR)
            out[s:s + len(nn)] += nn
        t0 += beat * 4
        bar += 1
    out = out[:n]
    fade = int(SR * 1.5)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[:int(SR * 0.5)] *= np.linspace(0, 1, int(SR * 0.5))
    return out


# ============ 描画ヘルパー ============
_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def ease_out_cubic(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.9):
    x = min(max(x, 0), 1)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def ease_in_cubic(x):
    x = min(max(x, 0), 1)
    return x ** 3


def prog(t, start, dur):
    return min(max((t - start) / dur, 0), 1)


def text_img(text, f, fill, stroke=0, stroke_fill=None):
    bb = f.getbbox(text, stroke_width=stroke)
    pad = 8
    im = Image.new("RGBA", (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=f, fill=fill,
                            stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def fit_text_img(text, path, max_w, start, fill):
    size = start
    while size > 30:
        im = text_img(text, font(path, size), fill)
        if im.width <= max_w:
            return im
        size -= 4
    return text_img(text, font(path, size), fill)


def pill_img(text, f, bg, fg, padx=30, h=64):
    t = text_img(text, f, fg)
    im = Image.new("RGBA", (t.width + padx * 2, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, h - 1], radius=h // 2, fill=bg)
    im.alpha_composite(t, ((im.width - t.width) // 2, (h - t.height) // 2))
    return im


def place(base, im, cx, cy, scale=1.0, alpha=1.0, angle=0.0):
    """im を中心 (cx, cy) に、拡大率・透明度・回転を付けて合成する。"""
    if alpha <= 0.01 or scale <= 0.01:
        return
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        im = im.copy()
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im.putalpha(a)
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    # 画面外にはみ出す部分を切り取る
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(im.width, W - x), min(im.height, H - y)
    if ex <= sx or ey <= sy:
        return
    if (sx, sy, ex, ey) != (0, 0, im.width, im.height):
        im = im.crop((sx, sy, ex, ey))
    base.alpha_composite(im, (x + sx, y + sy))


def wrap(text, f, max_w):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, cur = [], ""
    for ch in text:
        if d.textbbox((0, 0), cur + ch, font=f)[2] > max_w and cur and ch not in "、。！？」』）":
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


# ============ 共通レイヤー ============
def make_background():
    img = Image.new("RGB", (W, H))
    arr = np.zeros((H, W, 3), dtype=np.float32)
    t = np.linspace(0, 1, H)[:, None]
    for i in range(3):
        arr[:, :, i] = BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    # うっすら斜めストライプ
    stripe = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stripe)
    for x in range(-H, W, 90):
        sd.line([(x, H), (x + H, 0)], fill=(255, 255, 255, 40), width=30)
    img.alpha_composite(stripe)
    return img


def blob(r, color, a):
    im = Image.new("RGBA", (r * 2 + 120, r * 2 + 120), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([60, 60, 60 + r * 2, 60 + r * 2], fill=color + (a,))
    return im.filter(ImageFilter.GaussianBlur(28))


class Common:
    def __init__(self):
        self.bg = make_background()
        self.blobs = [(blob(260, ACCENT_SOFT, 90), 140, 300, 0.0),
                      (blob(320, ACCENT_SOFT, 70), 960, 950, 2.0),
                      (blob(220, (250, 214, 228), 70), 180, 1600, 4.0),
                      (blob(180, (255, 236, 180), 80), 900, 1700, 1.0)]
        rng = random.Random(7)
        self.particles = []
        for _ in range(22):
            r = rng.randint(6, 16)
            col = rng.choice([(255, 255, 255), YELLOW, ACCENT_SOFT, (250, 214, 228)])
            sp = Image.new("RGBA", (r * 4, r * 4), (0, 0, 0, 0))
            ImageDraw.Draw(sp).ellipse([r, r, r * 3, r * 3], fill=col + (200,))
            sp = sp.filter(ImageFilter.GaussianBlur(2))
            self.particles.append((sp, rng.uniform(0, W), rng.uniform(0, H), rng.uniform(40, 110),
                                   rng.uniform(0, 6.28)))
        self.header = pill_img("穏やかな人が多い企業10選", font(BOLD, 48), ACCENT, (255, 255, 255),
                               padx=60, h=110)
        self.credit = text_img("VOICEVOX:四国めたん", font(MED, 30), (90, 110, 100))
        self.note = text_img("※口コミ等の一般的な評判に基づく。順位ではありません", font(MED, 26), (120, 135, 128))
        self.label = pill_img("四国めたん", font(BOLD, 34), METAN, (255, 255, 255), padx=26, h=60)

    def base(self, T):
        """T は動画全体の経過秒（背景がシーンをまたいでも連続して動くように）。"""
        img = self.bg.copy()
        for im, x, y, ph in self.blobs:
            place(img, im, x + 40 * math.sin(T * 0.5 + ph), y + 50 * math.cos(T * 0.4 + ph))
        for sp, x, y, v, ph in self.particles:
            yy = (y - v * T) % (H + 100) - 50
            xx = x + 25 * math.sin(T * 1.2 + ph)
            place(img, sp, xx, yy, alpha=0.5 + 0.5 * math.sin(T * 2 + ph) ** 2)
        return img

    def footer(self, img):
        place(img, self.credit, W - 50 - self.credit.width / 2, H - 110)
        place(img, self.note, W / 2, H - 60)


class Subtitle:
    """吹き出し型の字幕。文字は語りに合わせて少しずつ表示し、横に音量メーターを出す。"""

    def __init__(self, common, text, voice, narr_dur):
        self.c = common
        self.f = font(BOLD, 46)
        self.lines = wrap(text, self.f, W - 180)
        self.voice = voice
        self.narr_dur = narr_dur
        self.lh = 68
        self.h = self.lh * len(self.lines) + 64
        self.box = Image.new("RGBA", (W - 120, self.h), (0, 0, 0, 0))
        ImageDraw.Draw(self.box).rounded_rectangle([0, 0, W - 121, self.h - 1], radius=36,
                                                   fill=(255, 255, 255, 235), outline=METAN, width=5)
        self.cy = H - 360 - self.h / 2
        self.nchars = sum(len(l) for l in self.lines)
        # フレームごとの音量（RMS）
        hop = SR // FPS
        nfr = len(voice) // hop + 1
        pad = np.pad(voice, (0, nfr * hop - len(voice)))
        self.rms = np.sqrt((pad.reshape(nfr, hop) ** 2).mean(axis=1))
        self.rms /= max(self.rms.max(), 1e-6)

    def draw(self, img, t, scene_dur):
        p_in = ease_out_back(prog(t, 0.0, 0.35), 1.5)
        p_out = ease_in_cubic(prog(t, scene_dur - OUT_T, OUT_T))
        scale = 0.6 + 0.4 * p_in
        alpha = min(1, prog(t, 0, 0.15)) * (1 - p_out)
        cy = self.cy + 40 * p_out
        place(img, self.box, W / 2, cy, scale=scale, alpha=alpha)
        if p_in < 0.98 or alpha < 0.05:
            return
        # 文字の表示（語りの長さの 85% で全文が出るように）
        nt = t - LEAD
        shown = self.nchars if nt >= self.narr_dur * 0.85 else int(self.nchars * max(nt, 0) / (self.narr_dur * 0.85))
        d = ImageDraw.Draw(img, "RGBA")
        top = cy - self.h / 2 + 32
        left_all = []
        for line in self.lines:
            bb = d.textbbox((0, 0), line, font=self.f)
            left_all.append((W - (bb[2] - bb[0])) / 2 - bb[0])
        k = shown
        for i, line in enumerate(self.lines):
            part = line[:max(0, min(len(line), k))]
            k -= len(line)
            if part:
                d.text((left_all[i], top + i * self.lh), part, font=self.f,
                       fill=INK + (int(255 * alpha),))
        # 話者ラベル + 音量メーター
        ly = cy - self.h / 2
        bob = 4 * math.sin(t * 8) if 0 < nt < self.narr_dur else 0
        place(img, self.c.label, 100 + self.c.label.width / 2, ly + bob, alpha=alpha)
        fi = int(nt * FPS)
        lvl = self.rms[fi] if 0 <= fi < len(self.rms) else 0
        x0 = 100 + self.c.label.width + 24
        for j in range(5):
            wob = 0.55 + 0.45 * math.sin(t * 22 + j * 1.7)
            bh = 8 + 40 * lvl * wob
            d.rounded_rectangle([x0 + j * 16, ly - bh / 2, x0 + j * 16 + 9, ly + bh / 2], radius=4,
                                fill=METAN + (int(255 * alpha),))


# ============ シーン ============
class IntroScene:
    def __init__(self, c):
        self.c = c
        self.pill = pill_img("就活・転職の参考に", font(BOLD, 44), METAN, (255, 255, 255), h=90, padx=50)
        self.l1 = text_img("穏やかな人が多い", font(BOLD, 100), INK, 10, (255, 255, 255))
        self.l2 = text_img("と言われる企業", font(BOLD, 88), INK, 10, (255, 255, 255))
        self.big = text_img("10選", font(BOLD, 260), ACCENT, 16, (255, 255, 255))
        rng = random.Random(3)
        self.sparks = [(rng.uniform(0, 6.28), rng.uniform(260, 420), rng.choice([YELLOW, METAN, ACCENT]))
                       for _ in range(14)]
        self.se = [(0.05, "whoosh"), (0.35, "pop"), (0.6, "pop"), (0.95, "slam")]

    def draw(self, img, t, dur):
        po = ease_in_cubic(prog(t, dur - OUT_T, OUT_T))
        a = 1 - po
        p = ease_out_back(prog(t, 0.05, 0.45))
        place(img, self.pill, W / 2, 430 - 300 * (1 - p), alpha=a)
        p1 = ease_out_back(prog(t, 0.35, 0.4))
        place(img, self.l1, W / 2 - 1200 * po, 640, scale=p1, alpha=a)
        p2 = ease_out_back(prog(t, 0.6, 0.4))
        place(img, self.l2, W / 2 + 1200 * po, 780, scale=p2, alpha=a)
        # 「10選」はドンと落ちてきて画面が揺れる
        pb = prog(t, 0.95, 0.3)
        if pb > 0:
            s = 2.6 - 1.6 * ease_out_cubic(pb)
            pulse = 1 + 0.03 * math.sin(max(0, t - 1.4) * 5)
            shake = 18 * math.exp(-(t - 1.25) * 12) * math.sin(t * 90) if t > 1.25 else 0
            place(img, self.big, W / 2 + shake, 1030 + shake * 0.5, scale=s * pulse, alpha=min(1, pb * 3) * a,
                  angle=-4 * (1 - ease_out_cubic(pb)))
        # はじけるキラキラ
        ps = prog(t, 1.2, 0.8)
        if 0 < ps < 1:
            d = ImageDraw.Draw(img, "RGBA")
            for ang, dist, col in self.sparks:
                r = dist * ease_out_cubic(ps)
                x, y = W / 2 + r * math.cos(ang), 1030 + r * math.sin(ang) * 0.7
                sz = 14 * (1 - ps)
                d.ellipse([x - sz, y - sz, x + sz, y + sz], fill=col + (int(255 * (1 - ps)),))


class CompanyScene:
    def __init__(self, c, i, name, tag, reasons):
        self.c, self.i = c, i
        card = Image.new("RGBA", (W - 140 + 80, 830 + 80), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle([40, 54, 40 + W - 140, 54 + 830], radius=50, fill=(40, 70, 60, 60))
        card = card.filter(ImageFilter.GaussianBlur(18))
        ImageDraw.Draw(card).rounded_rectangle([40, 40, 40 + W - 140, 40 + 830], radius=50, fill=(255, 255, 255))
        self.card = card
        r = 95
        badge = Image.new("RGBA", (r * 2 + 20, r * 2 + 20), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.ellipse([10, 10, 10 + r * 2, 10 + r * 2], fill=ACCENT)
        bd.ellipse([22, 22, r * 2 - 2, r * 2 - 2], outline=(255, 255, 255, 90), width=4)
        num = text_img(str(i + 1), font(BOLD, 110), (255, 255, 255))
        badge.alpha_composite(num, ((badge.width - num.width) // 2, (badge.height - num.height) // 2 - 4))
        self.badge = badge
        self.tag = pill_img(tag, font(BOLD, 38), ACCENT_SOFT, ACCENT, h=62)
        self.name = fit_text_img(name, BOLD, W - 220, 120, INK)
        self.reasons = [text_img(r, font(BOLD, 52), SUB_INK) for r in reasons]
        # 理由の下に引く黄色マーカー
        self.markers = [Image.new("RGBA", (im.width - 10, 22), YELLOW + (170,)) for im in self.reasons]
        self.se = [(0.02, "whoosh"), (0.25, "pop"), (0.55, "whoosh"), (0.95, "pop"), (1.25, "pop")]

    def draw(self, img, t, dur):
        c = self.c
        # ヘッダーと進み具合
        place(img, c.header, W / 2, 170)
        d = ImageDraw.Draw(img, "RGBA")
        n, gap = len(COMPANIES), 70
        x0 = (W - gap * (n - 1)) / 2
        for k in range(n):
            cx, cy = x0 + k * gap, 290
            if k == self.i:
                r = 12 + 5 * ease_out_back(prog(t, 0.1, 0.4)) + 2 * math.sin(t * 6)
                fill = ACCENT
            else:
                r = 10
                fill = ACCENT if k < self.i else (205, 215, 210)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

        # 退場：カードごと左へスライド
        po = ease_in_cubic(prog(t, dur - OUT_T, OUT_T))
        ox = -W * 1.1 * po
        a_out = 1 - po
        # カード：下からバウンドして登場し、ゆらゆら浮く
        pc = ease_out_back(prog(t, 0.0, 0.45), 1.4)
        float_y = 6 * math.sin(t * 2.2)
        cy0 = 775 + 500 * (1 - pc) + float_y
        place(img, self.card, W / 2 + ox, cy0, alpha=min(1, prog(t, 0, 0.2)) * a_out,
              angle=3 * (1 - pc))
        dy = cy0 - 775  # カード内の要素はカードの動きに追従
        # 番号バッジ：ポンと弾ける
        pb = ease_out_back(prog(t, 0.25, 0.4), 2.6)
        pulse = 1 + 0.04 * math.sin(t * 5)
        place(img, self.badge, W / 2 + ox, 500 + dy, scale=pb * pulse, alpha=a_out,
              angle=-20 * (1 - ease_out_cubic(prog(t, 0.25, 0.4))))
        # 業界タグ
        pt = ease_out_cubic(prog(t, 0.45, 0.3))
        place(img, self.tag, W / 2 + ox, 660 + dy - 30 * (1 - pt), alpha=pt * a_out)
        # 社名：右からスライドイン
        pn = ease_out_back(prog(t, 0.55, 0.45), 1.3)
        place(img, self.name, W / 2 + 700 * (1 - pn) + ox, 790 + dy, alpha=min(1, prog(t, 0.55, 0.2)) * a_out)
        # 区切り線が伸びる
        pl = ease_out_cubic(prog(t, 0.85, 0.3))
        if pl > 0:
            hw = 90 * pl
            d.rounded_rectangle([W / 2 - hw + ox, 900 + dy - 3, W / 2 + hw + ox, 900 + dy + 3], radius=3,
                                fill=ACCENT + (int(255 * a_out),))
        # 理由：1行ずつ浮かび上がり、マーカーが引かれる
        for j, (im, mk) in enumerate(zip(self.reasons, self.markers)):
            st = 0.95 + 0.3 * j
            pr = ease_out_cubic(prog(t, st, 0.35))
            y = 985 + j * 90 + dy + 30 * (1 - pr)
            pm = ease_out_cubic(prog(t, st + 0.3, 0.4))
            if pm > 0:
                mw = max(1, int(mk.width * pm))
                place(img, mk.crop((0, 0, mw, mk.height)), W / 2 - mk.width / 2 + mw / 2 + ox, y + 22,
                      alpha=pr * a_out)
            place(img, im, W / 2 + ox, y, alpha=pr * a_out)


class OutroScene:
    def __init__(self, c):
        self.c = c
        self.l0 = pill_img("※雰囲気は部署・上司で変わります", font(BOLD, 48), METAN, (255, 255, 255), h=96, padx=44)
        self.l1 = text_img("口コミサイトやOB・OG訪問で", font(BOLD, 64), INK)
        self.l2 = text_img("自分の目で", font(BOLD, 110), ACCENT, 12, (255, 255, 255))
        self.l3 = text_img("確かめよう！", font(BOLD, 130), ACCENT, 12, (255, 255, 255))
        self.check = text_img("✔", font(BOLD, 120), YELLOW, 8, (255, 255, 255))
        self.se = [(0.05, "whoosh"), (0.3, "pop"), (1.0, "pop"), (1.6, "slam"), (2.0, "chime")]

    def draw(self, img, t, dur):
        place(img, self.c.header, W / 2, 170)
        p0 = ease_out_back(prog(t, 0.3, 0.4))
        place(img, self.l0, W / 2, 460, scale=p0)
        p1 = ease_out_cubic(prog(t, 1.0, 0.4))
        place(img, self.l1, W / 2, 640 + 40 * (1 - p1), alpha=p1)
        p2 = ease_out_back(prog(t, 1.6, 0.4), 2.2)
        place(img, self.l2, W / 2, 800, scale=p2)
        p3 = ease_out_back(prog(t, 1.75, 0.45), 2.2)
        wob = 1 + 0.035 * math.sin(max(0, t - 2.2) * 4.5)
        place(img, self.l3, W / 2, 960, scale=p3 * wob, angle=2 * math.sin(max(0, t - 2.2) * 3))
        pc = ease_out_back(prog(t, 2.0, 0.4), 3)
        place(img, self.check, W - 150, 820, scale=pc, angle=15)


# ============ メイン ============
def main():
    BUILD.mkdir(exist_ok=True)
    common = Common()
    sfx = {"pop": se_pop(), "whoosh": se_whoosh(), "slam": se_slam(), "chime": se_chime()}

    defs = [(IntroScene(common), INTRO_NARR)]
    for i, (name, tag, reasons, narr) in enumerate(COMPANIES):
        defs.append((CompanyScene(common, i, name, tag, reasons), narr))
    defs.append((OutroScene(common), OUTRO_NARR))

    scenes, T = [], 0.0
    for scene, narr in defs:
        voice = tts(narr)
        nd = len(voice) / SR
        dur = max(LEAD + nd + TAIL, 2.6)
        shown = narr
        for k, v in DISPLAY_FIX.items():
            shown = shown.replace(k, v)
        scenes.append((scene, Subtitle(common, shown, voice, nd), voice, T, dur))
        T += dur
    total = T
    print(f"total {total:.1f}s, {len(scenes)} scenes")

    # ---- 音声ミックス ----
    n = int(total * SR) + SR
    voice_tr = np.zeros(n)
    se_tr = np.zeros(n)
    for scene, sub, voice, st, dur in scenes:
        s = int((st + LEAD) * SR)
        voice_tr[s:s + len(voice)] += voice
        for at, name in scene.se:
            e = sfx[name]
            s = int((st + at) * SR)
            se_tr[s:s + len(e)] += e[:n - s]
    music = bgm(total + 1)[:n]
    music = np.pad(music, (0, n - len(music)))
    # ナレーション中は BGM を少し下げる（ダッキング）
    vol = np.convolve(np.abs(voice_tr), np.ones(SR // 5) / (SR // 5), "same")
    duck = 1 - 0.45 * np.clip(vol * 12, 0, 1)
    mix = voice_tr * 1.0 + se_tr * 0.55 + music * 0.32 * duck
    mix = mix[:int(total * SR)]
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    audio_path = BUILD / "mix.wav"
    with wave.open(str(audio_path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

    # ---- 映像 ----
    out = HERE / "calm_companies_short.mp4"
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
        "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest", "-movflags", "+faststart",
        str(out)], stdin=subprocess.PIPE)
    nframes = int(total * FPS)
    si = 0
    for f in range(nframes):
        Tg = f / FPS
        while si < len(scenes) - 1 and Tg >= scenes[si][3] + scenes[si][4]:
            si += 1
        scene, sub, voice, st, dur = scenes[si]
        t = Tg - st
        img = common.base(Tg)
        scene.draw(img, t, dur)
        sub.draw(img, t, dur)
        common.footer(img)
        # 場面の頭に一瞬白く光らせる
        if t < 0.12 and si > 0:
            flash = Image.new("RGBA", (W, H), (255, 255, 255, int(110 * (1 - t / 0.12))))
            img.alpha_composite(flash)
        ff.stdin.write(img.convert("RGB").tobytes())
        if f % 150 == 0:
            print(f"frame {f}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"-> {out}")


if __name__ == "__main__":
    main()
