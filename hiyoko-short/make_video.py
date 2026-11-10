#!/usr/bin/env python3
"""ヒヨコ鑑定士のショート動画（縦型 1080x1920）を作る。

ナレーションは VOICEVOX エンジン（四国めたん）で生成する。
エンジンが動いていない場合は --no-voice で無音の確認用動画を作れる。

使い方:
  python3 make_video.py                 # VOICEVOX (http://127.0.0.1:50021) を使う
  python3 make_video.py --no-voice      # ナレーションなしで映像だけ確認
"""
import argparse
import io
import json
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
FPS = 30
SR = 44100
FONT_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
VOICEVOX = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
GAP = 0.35  # 各シーンのナレーション後の間（秒）
LEAD_IN = 0.25

INK = (60, 40, 20)
ORANGE = (255, 140, 30)
RED = (235, 70, 70)
CHICK = (255, 214, 60)
CHICK_DARK = (240, 180, 30)

SCENE_BG = {
    "hook": ((255, 244, 200), (255, 214, 150)),
    "name": ((255, 236, 210), (255, 200, 170)),
    "same": ((225, 242, 255), (200, 225, 255)),
    "why": ((255, 238, 245), (250, 205, 225)),
    "stats": ((240, 255, 228), (205, 240, 190)),
    "world": ((225, 245, 255), (185, 225, 250)),
    "outro": ((255, 244, 200), (255, 205, 140)),
}


def font(size):
    return ImageFont.truetype(FONT_PATH, size)


# ---------------------------------------------------------------- 音声
def synth_voice(text, speaker):
    import urllib.parse
    import urllib.request

    q = urllib.parse.urlencode({"text": text, "speaker": speaker})
    req = urllib.request.Request(f"{VOICEVOX}/audio_query?{q}", method="POST")
    query = json.loads(urllib.request.urlopen(req, timeout=60).read())
    query["speedScale"] = 1.15
    query["intonationScale"] = 1.2
    query["prePhonemeLength"] = 0.05
    query["postPhonemeLength"] = 0.05
    query["outputSamplingRate"] = SR
    query["outputStereo"] = False
    req = urllib.request.Request(
        f"{VOICEVOX}/synthesis?speaker={speaker}",
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    data = urllib.request.urlopen(req, timeout=120).read()
    with wave.open(io.BytesIO(data)) as w:
        assert w.getframerate() == SR, w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0


def make_bgm(seconds):
    """明るめのチップチューン風ループ（その場で合成するのでライセンスの心配なし）。"""
    bpm = 128
    beat = 60 / bpm
    n = int(seconds * SR)
    out = np.zeros(n, dtype=np.float32)
    t_note = lambda dur: np.arange(int(dur * SR)) / SR

    def tone(freq, dur, kind="square", vol=0.2, decay=6.0):
        t = t_note(dur)
        ph = 2 * np.pi * freq * t
        if kind == "square":
            w = np.sign(np.sin(ph)) * 0.6 + np.sin(ph) * 0.4
        elif kind == "tri":
            w = 2 / np.pi * np.arcsin(np.sin(ph))
        else:
            w = np.sin(ph)
        env = np.exp(-decay * t) * np.minimum(1, t * 200)
        return (w * env * vol).astype(np.float32)

    def add(sig, start):
        s = int(start * SR)
        if s >= n:
            return
        e = min(n, s + len(sig))
        out[s:e] += sig[: e - s]

    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    # C - G - Am - F
    chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    bass = [36, 43, 45, 41]
    melody = [
        [72, None, 76, 79, 76, None, 74, 72],
        [71, None, 74, 79, 74, None, 72, 71],
        [72, None, 76, 81, 79, None, 76, 74],
        [72, 74, 76, None, 77, 76, 74, None],
    ]
    bar = beat * 4
    rng = np.random.default_rng(0)
    bars = int(seconds / bar) + 1
    for b in range(bars):
        c = b % 4
        t0 = b * bar
        for i in range(8):  # 8分刻みのコード刻み
            for m in chords[c]:
                add(tone(midi(m), beat * 0.45, "square", 0.035, 9), t0 + i * beat / 2)
        for i in range(4):
            add(tone(midi(bass[c]), beat * 0.9, "tri", 0.22, 3), t0 + i * beat)
            # キック
            kt = t_note(0.15)
            kick = np.sin(2 * np.pi * (120 * np.exp(-25 * kt)) * kt) * np.exp(-18 * kt) * 0.35
            add(kick.astype(np.float32), t0 + i * beat)
            # ハイハット
            hh = rng.standard_normal(int(0.04 * SR)).astype(np.float32)
            hh *= np.exp(-90 * t_note(0.04)).astype(np.float32) * 0.05
            add(hh, t0 + i * beat + beat / 2)
        if b >= 1:  # 2小節目からメロディ
            for i, m in enumerate(melody[c]):
                if m is not None:
                    add(tone(midi(m), beat * 0.5, "square", 0.06, 5), t0 + i * beat / 2)
    # フェードアウト
    fade = int(1.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


def build_audio(scene_voices, durations, total):
    n = int(total * SR) + SR
    voice = np.zeros(n, dtype=np.float32)
    t = LEAD_IN
    for pcm, d in zip(scene_voices, durations):
        s = int(t * SR)
        voice[s : s + len(pcm)] += pcm
        t += d
    bgm = make_bgm(n / SR)[:n]
    # 声が出ている間は BGM を下げる（簡易ダッキング）
    env = np.abs(voice)
    k = int(0.15 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    duck = np.clip(1 - env * 25, 0.35, 1.0)
    duck = np.convolve(duck, np.ones(k) / k, mode="same")
    mix = voice * 1.0 + bgm * 0.3 * duck
    peak = np.max(np.abs(mix))
    mix *= 0.9 / peak  # ピークを -1dB 付近にそろえる
    path = os.path.join(HERE, "build", "audio.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return path


# ---------------------------------------------------------------- 描画パーツ
def gradient(top, bottom):
    a = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top)[None, None] * (1 - a) + np.array(bottom)[None, None] * a)
    arr = np.repeat(arr, W, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def chick_sprite(size, flap=0.0, wink=False, color=CHICK, bow=False):
    """丸っこいヒヨコを 2 倍で描いて縮小（アンチエイリアス）。"""
    s = size * 2
    im = Image.new("RGBA", (s, int(s * 1.15)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = s // 2
    shade = tuple(max(0, c - 25) for c in color)
    # 足
    for dx in (-0.14, 0.14):
        fx = cx + dx * s
        d.line([(fx, s * 0.9), (fx, s * 1.02)], fill=ORANGE, width=int(s * 0.03))
        d.line([(fx - s * 0.05, s * 1.04), (fx + s * 0.05, s * 1.04)], fill=ORANGE, width=int(s * 0.03))
    # 体
    d.ellipse([s * 0.1, s * 0.3, s * 0.9, s * 0.98], fill=color, outline=INK, width=int(s * 0.018))
    # 羽（パタパタ）
    for side in (-1, 1):
        ang = 20 + flap * 35
        wing = Image.new("RGBA", (int(s * 0.3), int(s * 0.2)), (0, 0, 0, 0))
        wd = ImageDraw.Draw(wing)
        wd.ellipse([0, 0, wing.width - 1, wing.height - 1], fill=shade, outline=INK, width=int(s * 0.014))
        wing = wing.rotate(side * ang, expand=True, resample=Image.BICUBIC)
        wx = int(cx + side * s * 0.36 - wing.width / 2)
        im.alpha_composite(wing, (wx, int(s * 0.6 - wing.height / 2)))
    # 頭のアホ毛
    d.arc([cx - s * 0.04, s * 0.2, cx + s * 0.1, s * 0.34], 180, 360, fill=INK, width=int(s * 0.02))
    d.arc([cx - s * 0.1, s * 0.18, cx + s * 0.04, s * 0.32], 180, 360, fill=INK, width=int(s * 0.02))
    # 目
    for dx in (-0.15, 0.15):
        ex, ey = cx + dx * s, s * 0.52
        r = s * 0.045
        if wink and dx > 0:
            d.arc([ex - r, ey - r, ex + r, ey + r], 200, 340, fill=INK, width=int(s * 0.02))
        else:
            d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=INK)
            d.ellipse([ex - r * 0.2, ey - r * 0.7, ex + r * 0.4, ey - r * 0.1], fill="white")
    # ほっぺ
    for dx in (-0.25, 0.25):
        hx, hy = cx + dx * s, s * 0.62
        d.ellipse([hx - s * 0.05, hy - s * 0.03, hx + s * 0.05, hy + s * 0.03], fill=(255, 150, 140, 200))
    # くちばし
    d.polygon([(cx - s * 0.06, s * 0.6), (cx + s * 0.06, s * 0.6), (cx, s * 0.69)], fill=ORANGE, outline=INK)
    if bow:  # リボン
        bx, by = cx + s * 0.2, s * 0.32
        d.polygon([(bx, by), (bx - s * 0.1, by - s * 0.06), (bx - s * 0.1, by + s * 0.06)], fill=(255, 110, 160), outline=INK)
        d.polygon([(bx, by), (bx + s * 0.1, by - s * 0.06), (bx + s * 0.1, by + s * 0.06)], fill=(255, 110, 160), outline=INK)
        d.ellipse([bx - s * 0.025, by - s * 0.025, bx + s * 0.025, by + s * 0.025], fill=(255, 80, 140))
    return im.resize((size, int(size * 1.15)), Image.LANCZOS)


class ChickAnim:
    def __init__(self, size, **kw):
        self.frames = [chick_sprite(size, flap=f, **kw) for f in np.linspace(0, 1, 6)]
        self.blink = chick_sprite(size, wink=True, **kw)

    def get(self, t, flap_speed=6.0):
        if (t % 3.0) < 0.12:
            return self.blink
        f = (math.sin(t * flap_speed) + 1) / 2
        return self.frames[int(f * (len(self.frames) - 1))]


def text_img(lines, size, colors, stroke=14, spacing=1.15):
    f = font(size)
    if isinstance(colors, tuple):
        colors = [colors] * len(lines)
    widths = [f.getbbox(l, stroke_width=stroke)[2] for l in lines]
    lh = int(size * spacing)
    im = Image.new("RGBA", (max(widths) + stroke * 2, lh * len(lines) + stroke * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, (l, c) in enumerate(zip(lines, colors)):
        x = (im.width - widths[i]) // 2
        d.text((x, stroke + i * lh), l, font=f, fill=c, stroke_width=stroke, stroke_fill="white")
    # うっすら影
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadow.putalpha(im.getchannel("A").point(lambda a: int(a * 0.25)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    out = Image.new("RGBA", (im.width + 16, im.height + 16), (0, 0, 0, 0))
    out.alpha_composite(shadow, (12, 14))
    out.alpha_composite(im, (4, 4))
    return out


def fit_width(img, maxw):
    if img.width <= maxw:
        return img
    r = maxw / img.width
    return img.resize((maxw, int(img.height * r)), Image.LANCZOS)


def subtitle_img(text, maxw=940, size=50):
    f = font(size)
    lines = []
    for para in text.split("\n"):
        lines += _wrap(para, f, maxw)
    return _sub_box(lines, f, maxw, size)


def _wrap(text, f, maxw):
    lines, cur = [], ""
    for ch in text:
        if f.getlength(cur + ch) > maxw - 60:
            # 句読点を行頭に置かない
            if ch in "、。！？」』）":
                cur += ch
                continue
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def _sub_box(lines, f, maxw, size):
    lh = int(size * 1.35)
    box = Image.new("RGBA", (maxw, lh * len(lines) + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle([0, 0, box.width - 1, box.height - 1], radius=36, fill=(40, 25, 10, 205))
    for i, l in enumerate(lines):
        w = f.getlength(l)
        d.text(((maxw - w) / 2, 25 + i * lh), l, font=f, fill="white")
    return box


def ease_out_back(x):
    x = min(max(x, 0), 1)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def pop(img, t, delay=0.0, dur=0.35):
    k = ease_out_back((t - delay) / dur)
    if k <= 0.01:
        return None
    w, h = max(1, int(img.width * k)), max(1, int(img.height * k))
    return img.resize((w, h), Image.BILINEAR)


def paste_c(base, img, cx, cy):
    if img is None:
        return
    base.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


# ---------------------------------------------------------------- シーン
class Renderer:
    def __init__(self, scenes):
        self.scenes = scenes
        self.bg = {k: gradient(*v).convert("RGBA") for k, v in SCENE_BG.items()}
        self.chick = ChickAnim(420)
        self.chick_small = ChickAnim(300)
        self.chick_girl = ChickAnim(300, bow=True)
        self.chick_tiny = ChickAnim(170)
        self.heads, self.subs, self.smalls = [], [], []
        for sc in scenes:
            lines = sc["headline"]
            colors = [INK] * len(lines)
            colors[-1] = RED if sc["kind"] in ("hook", "why", "world") else ORANGE
            if sc["kind"] == "name":
                colors = [ORANGE]
            size = 150 if sc["kind"] in ("name", "same") else 120
            self.heads.append(fit_width(text_img(lines, size, colors), 1000))
            self.subs.append(subtitle_img(sc["subtitle"]))
            self.smalls.append(text_img([sc["small"]], 60, INK, stroke=10) if sc.get("small") else None)
        self.q = text_img(["?"], 160, RED, stroke=12)
        self.egg = self._egg(260)
        self.globe = self._globe(560)
        self.f_stat_l = font(58)
        self.f_stat_b = font(110)
        self.follow = self._button("フォローする", 70)
        rnd = random.Random(1)
        self.dots = [(rnd.random() * W, rnd.random() * H, rnd.uniform(8, 26), rnd.uniform(20, 60)) for _ in range(26)]

    def _egg(self, size):
        s = size * 2
        im = Image.new("RGBA", (s, int(s * 1.3)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([8, 8, s - 8, im.height - 8], fill=(255, 250, 240), outline=INK, width=10)
        d.ellipse([s * 0.22, s * 0.25, s * 0.38, s * 0.5], fill=(255, 255, 255))
        return im.resize((size, int(size * 1.3)), Image.LANCZOS)

    def _globe(self, size):
        s = size * 2
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([10, 10, s - 10, s - 10], fill=(110, 180, 240), outline=INK, width=12)
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).ellipse([16, 16, s - 16, s - 16], fill=255)
        land = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ld = ImageDraw.Draw(land)
        rnd = random.Random(3)
        for _ in range(9):
            x, y = rnd.uniform(0.1, 0.8) * s, rnd.uniform(0.15, 0.8) * s
            ld.ellipse([x, y, x + rnd.uniform(0.15, 0.3) * s, y + rnd.uniform(0.1, 0.2) * s], fill=(120, 200, 110))
        # 日本（右上に赤い点）
        jx, jy = s * 0.74, s * 0.36
        ld.ellipse([jx - 40, jy - 40, jx + 40, jy + 40], fill=(235, 60, 60), outline="white", width=10)
        im.paste(land, (0, 0), Image.composite(land.getchannel("A"), Image.new("L", (s, s), 0), mask))
        for frac in (0.3, 0.5, 0.7):
            d.arc([10, s * frac - s * 0.1, s - 10, s * frac + s * 0.1], 0, 180, fill=(255, 255, 255, 120), width=4)
        return im.resize((size, size), Image.LANCZOS)

    def _button(self, label, size):
        f = font(size)
        w = int(f.getlength(label)) + 140
        im = Image.new("RGBA", (w, size + 70), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, w - 1, im.height - 1], radius=im.height // 2, fill=RED)
        d.text((70, 33), label, font=f, fill="white")
        return im

    def frame(self, i, lt, total_t, total_dur):
        sc = self.scenes[i]
        kind = sc["kind"]
        im = self.bg[kind].copy()
        d = ImageDraw.Draw(im)
        # ふわふわ浮かぶ水玉
        for x, y, r, sp in self.dots:
            yy = (y - total_t * sp) % (H + 60) - 30
            d.ellipse([x - r, yy - r, x + r, yy + r], fill=(255, 255, 255, 110))
        bob = math.sin(total_t * 5) * 14

        # 見出し
        head = pop(self.heads[i], lt, 0.0)
        paste_c(im, head, W / 2, 380)

        if kind == "hook":
            c = self.chick.get(total_t, 9)
            paste_c(im, pop(c, lt, 0.15), W / 2, 1050 + bob)
            # 「1秒」タイマー
            r = 120
            cx, cy = 820, 760
            k = min(1, max(0, (lt - 0.3) / 1.0))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="white", outline=INK, width=8)
            d.pieslice([cx - r + 16, cy - r + 16, cx + r - 16, cy + r - 16], -90, -90 + 360 * k, fill=(255, 120, 100))
            sec = font(64)
            d.text((cx - sec.getlength("1秒") / 2, cy - 34), "1秒", font=sec, fill=INK, stroke_width=6, stroke_fill="white")
        elif kind == "name":
            c = self.chick.get(total_t)
            paste_c(im, pop(c, lt, 0.1), W / 2 - 60, 1050 + bob)
            # 虫めがね
            mx, my = W / 2 + 230 + math.sin(total_t * 2) * 30, 900 + math.cos(total_t * 2) * 20
            if lt > 0.3:
                d.ellipse([mx - 110, my - 110, mx + 110, my + 110], fill=(200, 235, 255, 90), outline=INK, width=16)
                d.line([(mx + 78, my + 78), (mx + 200, my + 200)], fill=(120, 80, 40), width=34)
            paste_c(im, pop(self.smalls[i], lt, 0.45), W / 2, 590)
        elif kind == "same":
            a = self.chick_small.get(total_t)
            b = self.chick_small.get(total_t + 1.3)
            paste_c(im, pop(a, lt, 0.1), W / 2 - 230, 1050 + bob)
            paste_c(im, pop(b, lt, 0.25), W / 2 + 230, 1050 - bob)
            for k, x in enumerate((W / 2 - 230, W / 2 + 230)):
                paste_c(im, pop(self.q, lt, 0.4 + k * 0.15), x, 770 + math.sin(total_t * 6 + k) * 18)
        elif kind == "why":
            g = self.chick_girl.get(total_t)
            paste_c(im, pop(g, lt, 0.1), W / 2 - 180, 1060 + bob)
            paste_c(im, pop(self.egg, lt, 0.35), W / 2 + 230, 1080 + math.sin(total_t * 3) * 10)
            lab = font(60)
            if lt > 0.5:
                d.text((W / 2 - 180 - lab.getlength("メス") / 2, 1290), "メス", font=lab, fill=(230, 70, 130), stroke_width=8, stroke_fill="white")
        elif kind == "stats":
            for k, (label, value) in enumerate(sc["stats"]):
                y = 720 + k * 300
                appear = lt - 0.25 - k * 0.5
                if appear < 0:
                    continue
                slide = (1 - ease_out_back(appear / 0.4)) * 400
                x0, x1 = 90 + slide, 990 + slide
                d.rounded_rectangle([x0, y, x1, y + 250], radius=40, fill="white", outline=INK, width=6)
                d.text((x0 + 50, y + 30), label, font=self.f_stat_l, fill=INK)
                # 数字カウントアップ
                cnt = min(1, appear / 1.2)
                if "1000" in value:
                    shown = value.replace("1000", f"{int(1000 * cnt):d}")
                else:
                    shown = value.replace("100", f"{int(100 * cnt):d}")
                d.text((x0 + 50, y + 105), shown, font=self.f_stat_b, fill=RED, stroke_width=4, stroke_fill="white")
            c = self.chick_tiny.get(total_t, 12)
            paste_c(im, c, 880, 1380 + bob)
        elif kind == "world":
            g = pop(self.globe.rotate(math.sin(total_t) * 4, resample=Image.BICUBIC), lt, 0.1)
            paste_c(im, g, W / 2, 1000)
            for k in range(5):
                ang = total_t * 0.8 + k * 2 * math.pi / 5
                x = W / 2 + math.cos(ang) * 400
                y = 1000 + math.sin(ang) * 330
                if lt > 0.35 + k * 0.08:
                    paste_c(im, self.chick_tiny.get(total_t + k, 10), x, y)
        elif kind == "outro":
            c = self.chick.get(total_t, 14)
            jump = -abs(math.sin(total_t * 4)) * 60
            paste_c(im, pop(c, lt, 0.1), W / 2, 1000 + jump)
            paste_c(im, pop(self.smalls[i], lt, 0.3), W / 2, 590)
            k = 1 + 0.06 * math.sin(total_t * 8)
            btn = self.follow.resize((int(self.follow.width * k), int(self.follow.height * k)), Image.BILINEAR)
            paste_c(im, pop(btn, lt, 0.5), W / 2, 1330)

        # 字幕
        paste_c(im, pop(self.subs[i], lt, 0.0, 0.2), W / 2, 1560)
        # 進捗バー
        d.rectangle([0, 0, W, 14], fill=(255, 255, 255, 150))
        d.rectangle([0, 0, W * total_t / total_dur, 14], fill=ORANGE)
        return im.convert("RGB")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-voice", action="store_true", help="ナレーションなしで作る（確認用）")
    ap.add_argument("--out", default=os.path.join(HERE, "hiyoko_kanteishi_short.mp4"))
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, "script.json"), encoding="utf-8"))
    scenes = cfg["scenes"]
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)

    voices = []
    for sc in scenes:
        if args.no_voice:
            pcm = np.zeros(int(len(sc["voice"]) * 0.11 * SR), dtype=np.float32)
        else:
            try:
                pcm = synth_voice(sc["voice"], cfg["speaker_id"])
            except OSError as e:
                sys.exit(f"VOICEVOX エンジン ({VOICEVOX}) に接続できません: {e}\n"
                         "エンジンを起動するか、--no-voice を付けて実行してください。")
        voices.append(pcm)
        print(f"  {len(pcm) / SR:5.2f}s  {sc['subtitle']!r}")

    durations = [len(p) / SR + GAP for p in voices]
    durations[0] += LEAD_IN
    durations[-1] += 1.2  # 最後は少し余韻
    total = sum(durations)
    print(f"total {total:.1f}s")
    audio = build_audio(voices, [len(p) / SR + GAP for p in voices], total)

    r = Renderer(scenes)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", audio,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out],
        stdin=subprocess.PIPE,
    )
    starts = np.cumsum([0] + durations[:-1])
    nframes = int(total * FPS)
    for f in range(nframes):
        t = f / FPS
        i = int(np.searchsorted(starts, t, side="right") - 1)
        ff.stdin.write(r.frame(i, t - starts[i], t, total).tobytes())
        if f % 150 == 0:
            print(f"  frame {f}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("done:", args.out)


if __name__ == "__main__":
    main()
