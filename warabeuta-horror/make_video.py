#!/usr/bin/env python3
"""わらべうた系ホラー・ショート動画「七つ目の数え歌」生成スクリプト (v2).

縦型 1080x1920 / 30fps / 約50秒。ナレーションは Open JTalk（オフライン音声合成）、
それ以外の映像・音声もすべてプログラムで生成する。

使い方:  python3 make_video.py [出力パス]
必要:    ffmpeg, numpy, Pillow, open-jtalk (+ naist-jdic, nitech m001 voice), IPAフォント

構成
  0. つかみ   「この動画、最後まで聴かないでください。」
  1. ルール   七つ目を歌うと、鳥居の奥から“何か”が来る
  2. 数え歌   ひとつ…むっつ（数えるたびに影が近づく）
  3. 静寂     むっつで、やめた。…やめたはずだった。
  4. ななつ   誰かが七つ目を歌う（影が目の前に）
  5. やっつ   わたしは歌っていない／声は、うしろから
  6. 振り向く → 顔「みぃつけた」
  7. 余韻     ここのつ目は、あなたの番。（冒頭にループする）
"""
import hashlib
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
SR = 44100
HERE = Path(__file__).resolve().parent
BUILD = HERE / ".build"
BUILD.mkdir(exist_ok=True)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "kazoeuta_horror.mp4"

MINCHO = "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf"
GOTHIC = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
try:
    ImageFont.truetype(MINCHO, 10)
except OSError:
    MINCHO = GOTHIC
JT_DIC = "/var/lib/mecab/dic/open-jtalk/naist-jdic"
JT_VOICE = "/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice"

rng = np.random.default_rng(7)


# ================================================================ 音声ユーティリティ
def fftconv(x, k):
    n = len(x) + len(k) - 1
    nf = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(k, nf), nf)[:n]


def reverb_ir(sec, decay, seed=1):
    r = np.random.default_rng(seed)
    t = np.arange(int(sec * SR)) / SR
    ir = r.standard_normal(len(t)) * np.exp(-t * decay)
    ir = np.convolve(ir, np.ones(6) / 6, mode="same")   # 少し丸める
    ir[0] = 0
    return ir / np.sqrt(np.sum(ir ** 2))


def resample(x, ratio):
    """ratio>1 で長く・低く."""
    n = int(len(x) * ratio)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def smooth(x, win):
    return np.convolve(x, np.ones(win) / win, mode="same")


def tts(text, speed, pitch, alpha=0.55):
    key = hashlib.md5(f"{text}|{speed}|{pitch}|{alpha}".encode()).hexdigest()[:12]
    path = BUILD / f"tts_{key}.wav"
    if not path.exists():
        subprocess.run(["open_jtalk", "-x", JT_DIC, "-m", JT_VOICE, "-r", str(speed), "-fm", str(pitch),
                        "-a", str(alpha), "-ow", str(path)], input=text.encode(), check=True)
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    x = resample(x, SR / sr)
    # 前後の無音を詰める
    idx = np.where(np.abs(x) > 0.01)[0]
    x = x[max(0, idx[0] - 400): idx[-1] + 2000]
    return x / (np.max(np.abs(x)) + 1e-9)


IR_ROOM = reverb_ir(0.7, 7, 1)
IR_HALL = reverb_ir(2.2, 2.6, 2)


def narrator(text):
    """古いカセットに録音された語り（こもり＋ヒス）."""
    x = tts(text, 0.86, -3)
    x = smooth(x, 4) - 0.6 * smooth(x, 200)              # 帯域を狭めてラジオっぽく
    wet = fftconv(x, IR_ROOM)[: len(x) + int(0.5 * SR)]
    y = np.pad(x, (0, len(wet) - len(x))) + 0.12 * wet
    y += rng.standard_normal(len(y)) * 0.004
    return y / np.max(np.abs(y)) * 0.8


def child(text, whisper=False, wet=0.45, speed=0.62, pitch=11):
    """子どもの声（高く・遅く・わずかに二重・残響）."""
    x = tts(text, speed, pitch, 0.5)
    x = x + 0.5 * resample(x, 1.012)[: len(x)]           # わずかなズレで不気味な二重声
    if whisper:
        env = smooth(np.abs(x), 300)
        nz = rng.standard_normal(len(x))
        nz = smooth(nz, 3) - smooth(nz, 25)              # 高域のささやき成分
        x = 0.25 * x + 5.0 * env * nz
    tail = fftconv(x, IR_HALL)[: len(x) + int(1.8 * SR)]
    y = np.pad(x, (0, len(tail) - len(x))) + wet * tail
    return y / np.max(np.abs(y)) * 0.85


def pluck(freq, dur, amp=0.5, bright=1.0):
    """琴っぽい撥弦音."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k in range(1, 9):
        f = freq * k * (1 + 0.0007 * k * k)
        if f > SR / 2:
            break
        sig += (1.0 / k ** 1.25) * np.exp(-(2.2 + k * 1.3 / bright) * t) * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    return amp * sig * np.minimum(1, t / 0.004)


# ================================================================ 台本とタイムライン
LYRICS = [
    ("ひとつ", "ひとつ　ひとりで　かくれんぼ"),
    ("ふたつ", "ふたつ　ふりむきゃ　おにがくる"),
    ("みっつ", "みっつ　みつけて　もらえぬこ"),
    ("よっつ", "よっつ　よなかに　かぞえてる"),
    ("いつつ", "いつつ　いつまで　まっている"),
    ("むっつ", "むっつ　むかえに　いきますよ"),
]
LINE = 2.45
NOTE = LINE / 8


class TL:
    """ナレーションの長さからタイムラインを組み立てる."""

    def __init__(self):
        self.t = 0.0
        self.voice = []     # (start, signal, pan, gain)
        self.subs = []      # (start, end, text, style)
        self.mark = {}

    def say(self, sig, text, style="narr", pan=0.0, gain=1.0, gap=0.35, sub_extra=0.25):
        st = self.t
        loud = np.where(np.abs(sig) > 0.08)[0]
        dur = (loud[-1] if len(loud) else len(sig)) / SR   # 残響の尾は次と重ねる
        self.voice.append((st, sig, pan, gain))
        if text:
            self.subs.append((st, st + dur + sub_extra, text, style))
        self.t = st + dur + gap
        return st

    def wait(self, sec):
        self.t += sec


def build_timeline():
    tl = TL()
    tl.wait(0.25)
    tl.mark["hook"] = tl.t
    tl.say(narrator("この動画、最後まで、聴かないでください。"), "この動画、最後まで\n聴かないでください。", gap=0.6)

    tl.mark["setup"] = tl.t
    tl.say(narrator("祖母の村には、七つ目を、歌ってはいけない、数え歌がある。"), "祖母の村には\n七つ目を歌ってはいけない\n数え歌がある。")
    tl.mark["figure_far"] = tl.t
    tl.say(narrator("ひとつ数えるたびに、鳥居の奥から、なにかが、一歩ずつ、近づいてくるから。"),
           "ひとつ数えるたびに\n鳥居の奥から“なにか”が\n一歩ずつ近づいてくるから。", gap=0.5)

    tl.mark["song"] = tl.t
    for i, (word, _) in enumerate(LYRICS):   # 子どもの声で数える（遠く・小さく）
        tl.voice.append((tl.t + i * LINE, child(word, wet=0.7), 0.0, 0.32 + 0.04 * i))
    tl.t += LINE * len(LYRICS)
    tl.mark["stop"] = tl.t
    tl.wait(0.9)
    tl.say(narrator("むっつで、やめた。"), "むっつで、やめた。", gap=0.5)
    tl.say(narrator("やめた、はずだった。"), "……やめた、はずだった。", gap=1.0)

    tl.mark["nanatsu"] = tl.t
    tl.say(child("ななつ。", wet=0.3, speed=0.55), "「ななつ」", style="child", gap=1.0, sub_extra=0.8)

    tl.mark["empty"] = tl.t
    tl.say(narrator("わたしは、歌っていない。"), "わたしは、歌っていない。", gap=0.8)
    tl.mark["yattsu"] = tl.t
    tl.say(child("やっつ。", whisper=True, wet=0.15, speed=0.6), "「やっつ」", style="child", pan=-0.85, gain=1.1,
           gap=0.4, sub_extra=0.6)
    tl.say(narrator("声は、すぐ、うしろから、聞こえた。"), "声は\nすぐ、うしろから聞こえた。", gap=0.3)
    tl.wait(0.7)                                   # 完全な無音
    tl.mark["whip"] = tl.t
    tl.wait(0.35)
    tl.mark["scare"] = tl.t
    tl.voice.append((tl.t, child("みいつけた。", wet=0.2, speed=0.7, pitch=8), 0.0, 1.0))
    tl.subs.append((tl.t, tl.t + 1.9, "みぃつけた", "scare"))
    tl.wait(1.9)
    tl.mark["end"] = tl.t
    tl.wait(0.8)
    tl.say(child("ここのつ。", whisper=True, wet=0.5, speed=0.6), "", gap=0.2)
    tl.mark["end_text"] = tl.mark["end"] + 0.6
    tl.wait(2.4)
    tl.mark["dur"] = tl.t
    return tl


TLN = build_timeline()
M = TLN.mark
DUR = M["dur"]


# ================================================================ 音声ミックス
def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(buf) or i < 0:
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def make_audio():
    n = int(DUR * SR) + SR
    L = np.zeros(n)
    R = np.zeros(n)
    t = np.arange(n) / SR

    def add_st(start, sig, pan=0.0, gain=1.0):
        add(L, start, sig, gain * math.sqrt((1 - pan) / 2) * 1.414)
        add(R, start, sig, gain * math.sqrt((1 + pan) / 2) * 1.414)

    # ---- 環境音：風・ドローン（「振り向く」直前で消える）
    silence_from = M["whip"] - 0.7
    amb_env = np.clip(t / 2, 0, 1) * np.clip((silence_from - t) / 0.4, 0, 1)
    wind = smooth(rng.standard_normal(n), 60) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t) * np.sin(2 * np.pi * 0.31 * t))
    wind2 = smooth(rng.standard_normal(n), 60) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t + 2))
    L += wind * amb_env * 0.35
    R += wind2 * amb_env * 0.35
    grow = 1 + 1.2 * np.clip((t - M["song"]) / (M["nanatsu"] - M["song"]), 0, 1)
    drone = 0.05 * (np.sin(2 * np.pi * 55 * t) + 0.8 * np.sin(2 * np.pi * 56.4 * t) + 0.35 * np.sin(2 * np.pi * 77.9 * t))
    L += drone * amb_env * grow
    R += drone * amb_env * grow

    # ---- 数え歌（都節音階・行ごとに音程が狂っていく）
    base = 293.66
    ratios = {0: 1.0, 1: 16 / 15, 2: 4 / 3, 3: 3 / 2, 4: 8 / 5, 5: 2.0}
    phrase = [[3, 3, 2, 3, 4, 3, 2, 0], [3, 3, 2, 3, 5, 4, 3, 3], [4, 4, 3, 2, 3, 3, 2, 0],
              [2, 2, 3, 4, 3, 2, 1, 0], [3, 3, 2, 3, 4, 3, 2, 0], [3, 4, 5, 4, 3, 2, 1, 1]]
    # 前奏：ナレーションの下で静かに
    for k, deg in enumerate([3, 3, 2, 0]):
        add_st(M["figure_far"] + 1.0 + k * NOTE * 1.5, pluck(base * ratios[deg], 1.2, 0.12), 0.2)
    for li, notes in enumerate(phrase):
        detune = 1 - 0.004 * li ** 1.6
        for ni, deg in enumerate(notes):
            st = M["song"] + li * LINE + ni * NOTE + (0.015 * li * rng.standard_normal() if li > 2 else 0)
            f = base * ratios[deg] * detune
            d = NOTE * (2.5 if ni == 7 else 1.6)
            add_st(st, pluck(f, d, 0.3), -0.15)
            if li >= 3:
                add_st(st + 0.025, pluck(f * 1.059, d, 0.05 * (li - 2)), 0.3)
    # 最後の音はブツッと切る
    cut = int(M["stop"] * SR)
    L[cut:cut + int(0.9 * SR)] *= 0
    R[cut:cut + int(0.9 * SR)] *= 0
    # 切れた瞬間のテープノイズ
    add_st(M["stop"], rng.standard_normal(int(0.08 * SR)) * 0.15)

    # ---- 心音（歌の後半〜「うしろ」まで、だんだん速く）
    hb_start, hb_end = M["song"] + LINE * 3, silence_from
    hb = hb_start
    while hb < hb_end:
        p = (hb - hb_start) / (hb_end - hb_start)
        m = int(0.25 * SR)
        tt = np.arange(m) / SR
        thump = np.sin(2 * np.pi * (46 + 30 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 18)
        add_st(hb, thump, 0, 0.3 + 0.4 * p)
        add_st(hb + 0.17, thump, 0, (0.3 + 0.4 * p) * 0.7)
        hb += 1.0 - 0.5 * p

    # ---- 「ななつ」：影が目の前に来る瞬間の低い衝撃音
    m = int(1.5 * SR)
    tt = np.arange(m) / SR
    hit = np.sin(2 * np.pi * (30 + 50 * np.exp(-tt * 10)) * tt) * np.exp(-tt * 3)
    add_st(M["nanatsu"] - 0.05, hit, 0, 0.7)

    # ---- 鈴（誰もいない参道）
    m = int(2.5 * SR)
    tt = np.arange(m) / SR
    bell = sum(np.sin(2 * np.pi * 1318 * r * tt) * np.exp(-tt * (3 + i)) / (i + 1)
               for i, r in enumerate([1, 2.76, 5.4, 8.93]))
    add_st(M["empty"] - 0.3, bell, 0.6, 0.12)

    # ---- 叫び（スティンガー）
    m = int(2.4 * SR)
    tt = np.arange(m) / SR
    env = np.exp(-tt * 1.4) * np.minimum(1, tt / 0.004)
    sting = np.zeros(m)
    for f in [311, 329.6, 349.2, 466.2, 493.9, 622.3, 659.3, 698.5]:
        ph = f * tt * (1 + 0.025 * np.sin(2 * np.pi * 6.5 * tt))
        sting += 2 * (ph % 1) - 1
    sting /= 8
    scream_nz = rng.standard_normal(m)
    scream_nz = smooth(scream_nz, 2) - smooth(scream_nz, 12)
    boom = np.sin(2 * np.pi * (32 + 70 * np.exp(-tt * 8)) * tt) * np.exp(-tt * 2.2)
    add_st(M["scare"], (0.55 * sting + 0.6 * scream_nz * np.exp(-tt * 2.5) + 0.9 * boom) * env, 0, 1.0)
    # 振り向くときの風切り音
    m = int(0.35 * SR)
    tt = np.arange(m) / SR
    sw = smooth(rng.standard_normal(m), 8) * np.sin(np.pi * tt / 0.35) ** 2
    add_st(M["whip"], sw, 0, 0.8)

    # ---- 声（ナレーション中は環境音・音楽を下げる）
    VL, VR = np.zeros(n), np.zeros(n)
    for st, sig, pan, gain in TLN.voice:
        add(VL, st, sig, gain * math.sqrt((1 - pan) / 2) * 1.414)
        add(VR, st, sig, gain * math.sqrt((1 + pan) / 2) * 1.414)
    venv = np.clip(smooth(np.abs(VL) + np.abs(VR), 4000) * 6, 0, 1)
    duck = 1 - 0.5 * venv
    # 叫びまでは全体を抑えて、叫びで一気に大きくする
    pre = np.where((t >= M["scare"]) & (t < M["scare"] + 2.4), 1.0, 0.42)
    L = L * duck * pre + VL * 0.95 * np.where(pre < 1, 0.55, 1.0)
    R = R * duck * pre + VR * 0.95 * np.where(pre < 1, 0.55, 1.0)

    # ---- 余韻：オルゴール一音
    add_st(M["end_text"] + 0.2, pluck(base * 2 * 0.98, 2.2, 0.1, bright=3), 0.1)

    st = np.stack([L, R], axis=1)[: int(DUR * SR)]
    st = np.tanh(st * 1.2) / np.tanh(1.2)
    st /= np.max(np.abs(st)) / 0.95
    return (st * 32767).astype(np.int16)


# ================================================================ 映像パーツ
def font(path, size):
    return ImageFont.truetype(path, size)


F_LYRIC = font(MINCHO, 70)
F_SUB = font(GOTHIC, 58)
F_CHILD = font(MINCHO, 96)
F_SCARE = font(MINCHO, 200)
F_END = font(MINCHO, 74)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = np.clip(1.25 - (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2) ** 1.1, 0, 1)[..., None]
SCAN = (1 - 0.06 * (np.arange(H) % 4 < 1)).astype(np.float32)[:, None, None]


def vtext(draw, x, y, text, fnt, fill, jitter=0.0):
    step = int(fnt.size * 1.12)
    cy = y
    for ch in text:
        if ch == "　":
            cy += step // 2
            continue
        bb = draw.textbbox((0, 0), ch, font=fnt)
        cw = bb[2] - bb[0]
        off = (fnt.size * 0.12, -fnt.size * 0.12) if ch in "っゃゅょぃ" else (0, 0)
        draw.text((x - cw / 2 + off[0] + rng.uniform(-jitter, jitter), cy + off[1] + rng.uniform(-jitter, jitter)),
                  ch, font=fnt, fill=fill)
        cy += step


def subtitle(draw, text, style, alpha):
    lines = text.split("\n")
    if style == "narr":
        fnt, fill, stroke = F_SUB, (int(235 * alpha),) * 3, (0, 0, 0)
        lh = 78
        y0 = 1380 - (len(lines) - 1) * lh / 2
    elif style == "child":
        fnt, fill, stroke = F_CHILD, (int(230 * alpha), int(30 * alpha), int(30 * alpha)), (0, 0, 0)
        lh = 110
        y0 = 820
    else:
        return
    for i, ln in enumerate(lines):
        bb = draw.textbbox((0, 0), ln, font=fnt)
        tw = bb[2] - bb[0]
        jit = 3 if style == "child" else 0
        draw.text(((W - tw) / 2 + rng.uniform(-jit, jit), y0 + i * lh), ln, font=fnt, fill=fill,
                  stroke_width=5, stroke_fill=stroke)


def make_face():
    """振り向いた先の顔（ジャンプスケア）."""
    img = Image.new("RGB", (W, H), (14, 3, 3))
    d = ImageDraw.Draw(img)
    cx, cy = W // 2 + 20, H // 2 - 40
    d.ellipse([cx - 560, cy - 760, cx + 560, cy + 900], fill=(6, 5, 5))           # 髪
    d.ellipse([cx - 360, cy - 520, cx + 360, cy + 600], fill=(205, 200, 192))     # 顔
    img = img.filter(ImageFilter.GaussianBlur(6))
    arr = np.asarray(img).astype(np.float32)
    # 立体感（下からの光）
    dist = ((xx - cx) / 380) ** 2 + ((yy - (cy + 160)) / 650) ** 2
    shade = np.clip(1.15 - 0.55 * dist, 0.25, 1.15)[..., None]
    arr *= shade

    def mask(draw_fn, blur):
        m = Image.new("L", (W, H), 0)
        draw_fn(ImageDraw.Draw(m))
        return (np.asarray(m.filter(ImageFilter.GaussianBlur(blur))).astype(np.float32) / 255)[..., None]

    # 落ちくぼんだ眼窩
    sockets = mask(lambda q: [q.ellipse([cx + s * 170 - 140, cy - 150 + (12 if s > 0 else 0),
                                         cx + s * 170 + 140, cy + 60 + (12 if s > 0 else 0)], fill=255)
                              for s in (-1, 1)], 38)
    arr *= 1 - 0.85 * sockets
    # 黒目（大きすぎる瞳）と小さな光
    eyes = mask(lambda q: [q.ellipse([cx + s * 170 - 70, cy - 95 + (12 if s > 0 else 0),
                                      cx + s * 170 + 70, cy + 15 + (12 if s > 0 else 0)], fill=255)
                           for s in (-1, 1)], 5)
    arr *= 1 - 0.97 * eyes
    hl = mask(lambda q: [q.ellipse([cx + s * 170 - 9, cy - 60, cx + s * 170 + 9, cy - 42], fill=255) for s in (-1, 1)], 2)
    arr += 200 * hl
    # 縦に開いた口
    mouth = mask(lambda q: q.ellipse([cx - 95, cy + 230, cx + 95, cy + 540], fill=255), 16)
    arr = arr * (1 - 0.95 * mouth) + np.array([40, 0, 0], np.float32) * mouth
    # 血の涙
    tears = mask(lambda q: [q.line([(cx + s * 170 + s * 25, cy + 30), (cx + s * 175 + s * 35, cy + 420)],
                                   fill=255, width=12) for s in (-1, 1)], 3)
    arr = arr * (1 - 0.8 * tears) + np.array([110, 0, 0], np.float32) * tears * 0.8
    # 顔にかかる髪の毛
    hair = Image.new("L", (W, H), 0)
    hd = ImageDraw.Draw(hair)
    r = np.random.default_rng(3)
    for _ in range(75):
        side = r.choice([-1, 1])
        x0 = cx + side * abs(r.normal(0, 1)) * 170 + side * 120
        x0 = cx + r.uniform(-60, 60) if r.random() < 0.15 else x0
        pts = [(x0, cy - 700)]
        x, y = x0, cy - 700
        length = r.uniform(500, 1500)
        while y < cy - 700 + length:
            y += 40
            x += r.uniform(-14, 14) + (x - cx) * 0.01
            pts.append((x, y))
        hd.line(pts, fill=255, width=int(r.uniform(2, 8)))
    hm = (np.asarray(hair.filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255)[..., None]
    arr *= 1 - 0.9 * hm
    arr *= 1 + 0.1 * rng.standard_normal((H, W, 1)).astype(np.float32)            # 肌のざらつき
    # 冷たい色＋少し傾ける
    arr = arr * np.array([0.95, 1.0, 1.05], np.float32)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).rotate(-7, resample=Image.BICUBIC,
                                                                        center=(cx, cy), fillcolor=(14, 3, 3))
    return np.asarray(img).astype(np.float32)


FACE = make_face()


def figure_layer(s, cx, by, tilt=0.0, eyes=False, beckon=None):
    """おかっぱの子どもの影（RGBAレイヤー）."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    hh = 300 * s
    rim = (110, 40, 36, 255)
    body = [(cx - 62 * s, by), (cx + 62 * s, by), (cx + 34 * s, by - hh * 0.62), (cx - 34 * s, by - hh * 0.62)]
    d.polygon(body, fill=(4, 3, 3, 255), outline=rim)
    if beckon is not None:
        ay = by - hh * 0.5 + beckon * 14 * s
        d.line([(cx + 30 * s, by - hh * 0.5), (cx + 82 * s, ay - 46 * s)], fill=(4, 3, 3, 255), width=max(2, int(14 * s)))
    hr = 40 * s
    neck = (cx, by - hh * 0.62)
    head = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(head)
    hy = neck[1] - hr * 0.9
    hrim = rim if s < 2 else (60, 22, 20, 255)
    # おかっぱ：丸い頭頂＋ギザギザに切りそろえた裾
    hd.ellipse([cx - hr * 1.1, hy - hr * 1.15, cx + hr * 1.1, hy + hr * 0.9], fill=(4, 3, 3, 255), outline=hrim,
               width=max(1, int(s * 1.5)))
    hem = [(cx - hr * 1.1, hy - hr * 0.1)]
    r_ = np.random.default_rng(5)
    for k in range(13):
        x = cx - hr * 1.1 + k * hr * 2.2 / 12
        hem.append((x, hy + hr * (1.15 + r_.uniform(-0.08, 0.12))))
    hem.append((cx + hr * 1.1, hy - hr * 0.1))
    hd.polygon(hem, fill=(4, 3, 3, 255))
    hd.line(hem, fill=hrim, width=max(1, int(s * 1.5)))
    if eyes:
        for ss in (-1, 1):
            ex = cx + ss * hr * 0.38
            r = max(1.5, hr * 0.07)
            hd.ellipse([ex - r, hy + hr * 0.25 - r, ex + r, hy + hr * 0.25 + r], fill=(235, 225, 215, 255))
    if tilt:
        head = head.rotate(tilt, resample=Image.BICUBIC, center=neck)
    lay.alpha_composite(head)
    return lay


def corridor(t, speed=0.5):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 8):
        k = y / H
        d.rectangle([0, y, W, y + 8], fill=(int(6 + 10 * k), int(7 + 6 * k), int(14 + 4 * k)))
    hz = int(H * 0.44)
    cx = W / 2 + 10 * math.sin(t * 0.4)
    d.polygon([(cx - 18, hz), (cx + 18, hz), (W * 0.95, H), (W * 0.05, H)], fill=(20, 18, 18))
    for r, c in ((260, (26, 14, 14)), (170, (40, 20, 18)), (90, (58, 28, 24))):
        d.ellipse([cx - r * 1.4, hz + 40 - r * 0.6, cx + r * 1.4, hz + 40 + r * 0.6], fill=c)
    cam = t * speed
    f = 2.2
    for z in sorted([i + (1.0 - cam % 1.0) + 0.5 for i in range(14)], reverse=True):
        s = f / z
        fog = max(0.0, min(1.0, 1.25 - z / 10))
        col = (int(120 * fog + 10), int(16 * fog + 6), int(14 * fog + 8))
        dark = (int(20 * fog + 6),) * 3
        gw, gh = 520 * s, 900 * s
        base_y = hz + 330 * s
        pw = max(2, 34 * s)
        x0, x1 = cx - gw, cx + gw
        top = base_y - gh
        d.rectangle([x0 + gw * 0.18 - pw, top, x0 + gw * 0.18 + pw, base_y], fill=col)
        d.rectangle([x1 - gw * 0.18 - pw, top, x1 - gw * 0.18 + pw, base_y], fill=col)
        d.polygon([(x0 - 40 * s, top - 40 * s), (x1 + 40 * s, top - 40 * s),
                   (x1 + 10 * s, top + 28 * s), (x0 - 10 * s, top + 28 * s)], fill=dark)
        d.rectangle([x0 + 10 * s, top + 28 * s, x1 - 10 * s, top + 62 * s], fill=col)
        d.rectangle([x0 + gw * 0.05, top + 170 * s, x1 - gw * 0.05, top + 200 * s], fill=col)
    return img, hz, cx


def post(arr, t, intensity, chroma=True):
    flick = 1 - 0.08 * (rng.random() < 0.15 + 0.3 * intensity) - 0.03 * math.sin(t * 50)
    arr = arr * VIGNETTE * flick
    if intensity > 0 and chroma:
        sh = int(3 + 16 * intensity)
        arr[..., 0] = np.roll(arr[..., 0], sh, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -sh, axis=1)
    grain = rng.normal(0, 9 + 10 * intensity, (H // 2, W // 2, 1)).astype(np.float32)
    grain = np.repeat(np.repeat(grain, 2, 0), 2, 1)
    return arr * SCAN + grain


def draw_subs(d, t):
    for st, en, text, style in TLN.subs:
        if st <= t < en:
            a = min(1, (t - st) / 0.15, (en - t) / 0.2)
            subtitle(d, text, style, max(0, a))


# ================================================================ フレーム
def render_frame(fi):
    t = fi / FPS
    f = 2.2

    # ---- 7. 余韻
    if t >= M["end"]:
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        if t >= M["end_text"]:
            a = min(1, (t - M["end_text"]) / 0.8)
            vtext(d, W / 2 + 70, 520, "ここのつ目は", F_END, (int(200 * a), int(190 * a), int(180 * a)))
            vtext(d, W / 2 - 70, 760, "あなたの番", F_END, (int(190 * a), 0, 0))
        return np.clip(post(np.asarray(img).astype(np.float32), t, 0), 0, 255).astype(np.uint8)

    # ---- 6. 顔
    if t >= M["scare"]:
        p = (t - M["scare"]) / (M["end"] - M["scare"])
        zoom = 1.0 + 0.3 * p
        img = Image.fromarray(FACE.astype(np.uint8))
        nw, nh = int(W * zoom), int(H * zoom)
        img = img.resize((nw, nh))
        amp = 45 * (1 - p) + 8
        ox = (nw - W) // 2 + int(rng.uniform(-amp, amp))
        oy = (nh - H) // 2 + int(rng.uniform(-amp, amp))
        img = img.crop((ox, oy, ox + W, oy + H))
        d = ImageDraw.Draw(img)
        msg = "みぃつけた"
        bb = d.textbbox((0, 0), msg, font=F_SCARE)
        for k in range(3):
            d.text(((W - (bb[2] - bb[0])) / 2 + rng.uniform(-14, 14), 1560 + rng.uniform(-10, 10)), msg,
                   font=F_SCARE, fill=(150 + 50 * k, 0, 0), stroke_width=4, stroke_fill=(0, 0, 0))
        arr = np.asarray(img).astype(np.float32)
        if fi % 5 == 0:
            arr = 255 - arr
        arr[..., 0] *= 1.2
        arr[..., 1:] *= 0.8
        arr *= max(0.0, 1 - max(0, p - 0.85) * 7)
        return np.clip(post(arr, t, 0.8, chroma=False), 0, 255).astype(np.uint8)

    # ---- 5→6. 振り向く（ウィップパン）
    if t >= M["whip"]:
        p = (t - M["whip"]) / (M["scare"] - M["whip"])
        img, _, _ = corridor(M["whip"], 0.5)
        base = np.asarray(img).astype(np.float32) * 0.5
        shift = int(W * 1.6 * p * p)
        acc = sum(np.roll(base, shift + k * int(40 + 200 * p), axis=1) for k in range(6)) / 6
        acc *= 1 - p * 0.7
        return np.clip(post(acc, t, 0.6), 0, 255).astype(np.uint8)

    # ---- 0. つかみ（暗闇、ときどき参道が見える）
    if t < M["setup"]:
        if fi < 3:     # 冒頭0.1秒、顔がちらっと映る
            arr = FACE * 0.55
        else:
            img, _, _ = corridor(t)
            arr = np.asarray(img).astype(np.float32) * (0.35 if rng.random() < 0.12 else 0.06)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        draw_subs(ImageDraw.Draw(img), t)
        return np.clip(post(np.asarray(img).astype(np.float32), t, 0.1), 0, 255).astype(np.uint8)

    # ---- 1〜5. 参道
    speed = 0.5 if t < M["stop"] else 0.0
    img, hz, cx = corridor(min(t, M["stop"]) if speed == 0 else t, 0.5)
    li = int((t - M["song"]) // LINE) if t >= M["song"] else -1
    fig = None
    if M["figure_far"] <= t < M["song"]:
        a = min(1, (t - M["figure_far"]) / 1.5)
        if a > 0.3:
            fig = (12.0, False, 0.0, None)
    elif M["song"] <= t < M["stop"]:
        fig = (12.0 / (1 + li * 0.85), li >= 3, 0.0, math.sin(t * 9) if li == 5 else None)
    elif M["stop"] <= t < M["nanatsu"]:
        fig = (12.0 / (1 + 5 * 0.85), True, 0.0, None)
    elif M["nanatsu"] <= t < M["empty"]:
        tilt = min(1, (t - M["nanatsu"]) / 1.6) * 28      # 目の前で首をかしげる
        fig = (0.55, True, tilt, None)
    if fig is not None:
        z, eyes, tilt, beck = fig
        s = f / z
        lay = figure_layer(s, cx, hz + 330 * s, tilt, eyes, beck)
        img = img.convert("RGBA")
        img.alpha_composite(lay)
        img = img.convert("RGB")
    d = ImageDraw.Draw(img)

    # 歌詞（縦書き、1文字ずつ）
    if M["song"] <= t < M["stop"] + 0.6:
        lii = min(li, len(LYRICS) - 1)
        text = LYRICS[lii][1]
        lt = t - (M["song"] + lii * LINE)
        nch = sum(1 for c in text if c != "　")
        shown = min(nch, int(lt / (LINE * 0.9) * nch) + 1)
        out, cnt = "", 0
        for c in text:
            if c != "　":
                if cnt >= shown:
                    break
                cnt += 1
            out += c
        col = (225, 215, 205) if lii < 4 else (225, 70, 60)
        vtext(d, W - 130, 230, out, F_LYRIC, col, jitter=max(0, lii - 2) * 1.5)
        # 何番目か（大きな漢数字）
        vtext(d, 120, 260, "一二三四五六"[lii], font(MINCHO, 150), (90, 20, 20))
    if M["nanatsu"] <= t < M["empty"]:
        vtext(d, 120, 260, "七", font(MINCHO, 150), (200, 20, 20), jitter=4)
    if M["yattsu"] <= t < M["whip"]:
        vtext(d, 120, 260, "八", font(MINCHO, 150), (200, 20, 20), jitter=4)
    draw_subs(d, t)

    arr = np.asarray(img).astype(np.float32)
    # 数え歌：行が変わる瞬間の暗転（その間に近づく）
    if li >= 1 and t < M["stop"]:
        if (t - M["song"]) - li * LINE < 0.08:
            arr *= 0.06
    # 「ななつ」直前の暗転
    if M["nanatsu"] - 0.25 <= t < M["nanatsu"]:
        arr *= 0.03
    if M["stop"] <= t:
        arr *= 0.75
    if M["whip"] - 0.7 <= t:        # 無音の間は暗く固まる
        arr *= 0.55
    intensity = 0.0
    if t >= M["song"]:
        intensity = min(1.0, (t - M["song"]) / (M["whip"] - M["song"])) * 0.35
    if M["nanatsu"] <= t < M["nanatsu"] + 0.4:
        intensity = 0.9
    return np.clip(post(arr, t, intensity), 0, 255).astype(np.uint8)


def main():
    print("timeline:", {k: round(v, 2) for k, v in M.items()}, flush=True)
    wav_path = BUILD / "audio.wav"
    audio = make_audio()
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(audio.tobytes())
    if "--audio-only" in sys.argv:
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav_path),
           "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 150 == 0:
            print(f"  {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("done:", OUT)


if __name__ == "__main__":
    main()
