#!/usr/bin/env python3
"""わらべうた系ホラー・ショート動画「かぞえうた」生成スクリプト.

縦型 1080x1920 / 30fps / 約30秒。映像・音声ともにすべてプログラムで生成する。
使い方:  python3 make_video.py [出力パス]
"""
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DUR = 28.4
SR = 44100
HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "kazoeuta_horror.mp4"

MINCHO = "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf"
GOTHIC = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
try:
    ImageFont.truetype(MINCHO, 10)
except OSError:
    MINCHO = GOTHIC

rng = np.random.default_rng(7)

# ---------------------------------------------------------------- 構成
T0 = 2.4          # 歌い出し
LINE = 2.8        # 1行の長さ
NOTE = LINE / 8   # 1音の長さ
LYRICS = [
    "ひとつ　ひとりで　かくれんぼ",
    "ふたつ　ふすまの　すきまから",
    "みっつ　みてるよ　だれかさん",
    "よっつ　よんでも　こたえない",
    "いつつ　いつまで　かくれるの",
    "むっつ　むこうで　てまねきを",
    "ななつ",
]
N_LINES = len(LYRICS)
T_STOP = T0 + LINE * 6 + NOTE * 3   # 「ななつ」で歌が止まる
T_WHISPER = T_STOP + 1.4             # 「うしろ」
T_SCARE = T_STOP + 3.3               # 顔
T_SCARE_END = T_SCARE + 1.6
T_END_TEXT = T_SCARE_END + 0.6


def line_index(t):
    if t < T0:
        return -1
    return min(int((t - T0) // LINE), N_LINES - 1)


# ---------------------------------------------------------------- 音声
def pluck(freq, dur, amp=0.5, bright=1.0):
    """琴っぽい撥弦音（倍音加算＋指数減衰）."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k in range(1, 9):
        f = freq * k * (1 + 0.0007 * k * k)
        if f > SR / 2:
            break
        decay = 2.2 + k * 1.3 / bright
        sig += (1.0 / k ** 1.25) * np.exp(-decay * t) * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    atk = np.minimum(1, t / 0.004)
    return amp * sig * atk


def add(buf, start, sig):
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def smooth_noise(n, win):
    k = np.ones(win) / win
    return np.convolve(rng.standard_normal(n), k, mode="same")


def make_audio():
    n = int(DUR * SR)
    music = np.zeros(n)
    fx = np.zeros(n)
    t = np.arange(n) / SR

    # 都節音階（D Eb G A Bb D）
    base = 293.66
    ratios = {0: 1.0, 1: 16 / 15, 2: 4 / 3, 3: 3 / 2, 4: 8 / 5, 5: 2.0, -1: 8 / 10, -2: 3 / 4}
    phrase = [
        [3, 3, 2, 3, 4, 3, 2, 0],
        [3, 3, 2, 3, 5, 4, 3, 3],
        [4, 4, 3, 2, 3, 3, 2, 0],
        [2, 2, 3, 4, 3, 2, 1, 0],
        [3, 3, 2, 3, 4, 3, 2, 0],
        [3, 4, 5, 4, 3, 2, 1, 1],
        [0, 1, 0],
    ]
    for li, notes in enumerate(phrase):
        detune = 1 - 0.0035 * li ** 1.6           # 少しずつ狂っていく
        for ni, deg in enumerate(notes):
            st = T0 + li * LINE + ni * NOTE + (0.012 * li * rng.standard_normal() if li > 2 else 0)
            f = base * ratios[deg] * detune
            d = NOTE * (2.4 if ni == len(notes) - 1 else 1.6)
            amp = 0.33 if li < N_LINES - 1 else 0.36
            add(music, st, pluck(f, d, amp))
            if li >= 4:  # 後半は不協な影が混ざる
                add(music, st + 0.02, pluck(f * 1.06, d, 0.06 * (li - 3)))
    # 「ななつ」の最後は伸ばして途切れる
    cut = int(T_STOP * SR + 0.35 * SR)
    fade = np.ones(n)
    fade[cut:cut + 800] = np.linspace(1, 0, 800)
    fade[cut + 800:] = 0
    music *= fade

    # ドローン（うなり）
    drone_env = np.clip((t - 0.3) / 3, 0, 1) * np.where(t < T_SCARE, 1, np.exp(-(t - T_SCARE) * 3))
    drone = 0.06 * (np.sin(2 * np.pi * 55 * t) + 0.8 * np.sin(2 * np.pi * 56.3 * t) + 0.3 * np.sin(2 * np.pi * 82.7 * t))
    fx += drone * drone_env * (1 + 0.6 * np.clip((t - 14) / 8, 0, 1))

    # 風
    wind = smooth_noise(n, 60) * 0.9
    wind_lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t + 1) * np.sin(2 * np.pi * 0.31 * t)
    wind_env = np.clip(t / 1.5, 0, 1) * np.where(t > T_SCARE, 0.25, 1)
    fx += wind * wind_lfo * wind_env * 0.45

    # 心音（後半、加速）
    hb_t = T0 + LINE * 3.5
    while hb_t < T_SCARE - 0.1:
        prog = (hb_t - (T0 + LINE * 3.5)) / (T_SCARE - (T0 + LINE * 3.5))
        for off, a in ((0, 1.0), (0.17, 0.7)):
            m = int(0.25 * SR)
            tt = np.arange(m) / SR
            thump = np.sin(2 * np.pi * (48 + 30 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 18)
            add(fx, hb_t + off, thump * a * (0.25 + 0.35 * prog))
        hb_t += 1.0 - 0.55 * prog

    # 歌が止まった後：鈴の音がひとつ
    bell_t = T_STOP + 0.9
    m = int(2.5 * SR)
    tt = np.arange(m) / SR
    bell = sum(np.sin(2 * np.pi * 1318 * r * tt) * np.exp(-tt * (3 + i)) / (i + 1)
               for i, r in enumerate([1, 2.76, 5.4, 8.93]))
    add(fx, bell_t, bell * 0.12)

    # 逆再生スウェル → 叫び
    sw_len = T_SCARE - T_WHISPER
    m = int(sw_len * SR)
    tt = np.arange(m) / SR
    rev = pluck(base * 0.75, sw_len, 0.5)[::-1] + pluck(base * 0.8, sw_len, 0.4)[::-1]
    rev *= (tt / sw_len) ** 2
    add(fx, T_WHISPER, rev * 0.6)

    # スティンガー
    m = int(2.2 * SR)
    tt = np.arange(m) / SR
    env = np.exp(-tt * 1.6) * np.minimum(1, tt / 0.005)
    sting = np.zeros(m)
    for f in [311, 329.6, 349, 466, 493.9, 622, 659]:
        ph = 2 * np.pi * f * tt * (1 + 0.02 * np.sin(2 * np.pi * 7 * tt))
        sting += 2 * ((ph / (2 * np.pi)) % 1) - 1   # のこぎり波
    sting = sting / 7 * 0.55
    sting += rng.standard_normal(m) * 0.5 * np.exp(-tt * 5)
    boom = np.sin(2 * np.pi * (35 + 60 * np.exp(-tt * 8)) * tt) * np.exp(-tt * 2.5) * 0.9
    add(fx, T_SCARE, (sting + boom) * env)

    # エンディング：オルゴール風の一音
    add(music, T_END_TEXT + 0.4, pluck(base * 2 * 0.985, 2.0, 0.12, bright=3))

    mix = music + fx
    mix = np.tanh(mix * 1.3) / np.tanh(1.3)
    mix /= max(1e-9, np.max(np.abs(mix))) / 0.92
    # ステレオ（風だけ左右にゆらす）
    pan = 0.5 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
    left = mix * (1 - 0.3 * pan) + wind * wind_env * 0.05 * pan
    right = mix * (0.7 + 0.3 * pan) + wind * wind_env * 0.05 * (1 - pan)
    st = np.stack([left, right], axis=1)
    st /= np.max(np.abs(st)) / 0.92
    return (st * 32767).astype(np.int16)


# ---------------------------------------------------------------- 映像パーツ
def font(path, size):
    return ImageFont.truetype(path, size)


F_LYRIC = font(MINCHO, 74)
F_TITLE = font(MINCHO, 120)
F_SMALL = font(GOTHIC, 34)
F_SCARE = font(MINCHO, 210)
F_END = font(MINCHO, 78)


def vtext(draw, x, y, text, fnt, fill, step=None, jitter=0.0):
    """縦書き（右上起点で下へ）。"""
    step = step or int(fnt.size * 1.12)
    cy = y
    for ch in text:
        if ch == "　":
            cy += step // 2
            continue
        dx = rng.uniform(-jitter, jitter)
        dy = rng.uniform(-jitter, jitter)
        bbox = draw.textbbox((0, 0), ch, font=fnt)
        cw = bbox[2] - bbox[0]
        if ch in "っゃゅょぃ":
            draw.text((x - cw / 2 + fnt.size * 0.12 + dx, cy - fnt.size * 0.12 + dy), ch, font=fnt, fill=fill)
        else:
            draw.text((x - cw / 2 + dx, cy + dy), ch, font=fnt, fill=fill)
        cy += step


def make_face():
    """少女の顔（ジャンプスケア用）。"""
    img = Image.new("RGB", (W, H), (46, 4, 4))
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2 + 60
    # 髪（おかっぱ）
    d.rounded_rectangle([cx - 520, cy - 760, cx + 520, cy + 420], radius=420, fill=(8, 6, 6))
    # 顔
    d.ellipse([cx - 380, cy - 520, cx + 380, cy + 560], fill=(214, 206, 196))
    # 前髪
    d.rectangle([cx - 450, cy - 800, cx + 450, cy - 230], fill=(8, 6, 6))
    for i in range(-9, 10):
        x = cx + i * 48
        d.polygon([(x - 30, cy - 240), (x + 30, cy - 240), (x + rng.uniform(-8, 8), cy - 180 - rng.uniform(0, 40))],
                  fill=(8, 6, 6))
    # 目（黒い穴）
    for s in (-1, 1):
        ex = cx + s * 165
        d.ellipse([ex - 105, cy - 120, ex + 105, cy + 20], fill=(0, 0, 0))
        d.ellipse([ex - 10, cy - 62, ex + 10, cy - 42], fill=(230, 230, 230))
        # 血の涙
        d.line([(ex + s * 20, cy + 15), (ex + s * 30, cy + 300)], fill=(120, 0, 0), width=14)
    # 口（裂けた笑み）
    d.chord([cx - 260, cy + 120, cx + 260, cy + 420], 0, 180, fill=(30, 0, 0))
    d.arc([cx - 262, cy + 118, cx + 262, cy + 422], 0, 180, fill=(140, 10, 10), width=10)
    for i in range(-5, 6):
        x = cx + i * 40
        d.rectangle([x - 14, cy + 268, x + 14, cy + 305], fill=(200, 190, 170))
    img = img.filter(ImageFilter.GaussianBlur(3))
    return np.asarray(img).astype(np.float32)


FACE = make_face()

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = np.clip(1.25 - (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2) ** 1.1, 0, 1)[..., None]
SCAN = (1 - 0.06 * (np.arange(H) % 4 < 1)).astype(np.float32)[:, None, None]


def draw_scene(t, li):
    """鳥居の回廊＋近づいてくる子ども."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    # 夜空グラデーション
    for y in range(0, H, 8):
        k = y / H
        c = (int(6 + 10 * k), int(7 + 6 * k), int(14 + 4 * k))
        d.rectangle([0, y, W, y + 8], fill=c)
    hz = int(H * 0.44)  # 地平線
    cx = W / 2 + 10 * math.sin(t * 0.4)
    # 参道
    d.polygon([(cx - 18, hz), (cx + 18, hz), (W * 0.95, H), (W * 0.05, H)], fill=(20, 18, 18))
    # 石灯籠の光の帯
    for s in (-1, 1):
        d.line([(cx + s * 18, hz), (W / 2 + s * W * 0.45, H)], fill=(34, 28, 26), width=3)

    # 奥の灯り（影を浮かび上がらせる）
    for r, c in ((260, (26, 14, 14)), (170, (40, 20, 18)), (90, (58, 28, 24))):
        d.ellipse([cx - r * 1.4, hz + 40 - r * 0.6, cx + r * 1.4, hz + 40 + r * 0.6], fill=c)

    cam = t * 0.55  # 前進
    f = 2.2
    gates = []
    for i in range(14):
        z = i + (1.0 - cam % 1.0) + 0.5
        gates.append(z)
    for z in sorted(gates, reverse=True):
        s = f / z
        fog = max(0.0, min(1.0, 1.25 - z / 10))
        col = (int(120 * fog + 10), int(16 * fog + 6), int(14 * fog + 8))
        dark = (int(20 * fog + 6),) * 3
        gw = 520 * s
        gh = 900 * s
        base_y = hz + 330 * s
        pw = max(2, 34 * s)
        x0, x1 = cx - gw, cx + gw
        top = base_y - gh
        # 柱
        d.rectangle([x0 + gw * 0.18 - pw, top, x0 + gw * 0.18 + pw, base_y], fill=col)
        d.rectangle([x1 - gw * 0.18 - pw, top, x1 - gw * 0.18 + pw, base_y], fill=col)
        # 笠木・島木
        d.polygon([(x0 - 40 * s, top - 40 * s), (x1 + 40 * s, top - 40 * s),
                   (x1 + 10 * s, top + 28 * s), (x0 - 10 * s, top + 28 * s)], fill=dark)
        d.rectangle([x0 + 10 * s, top + 28 * s, x1 - 10 * s, top + 62 * s], fill=col)
        # 貫
        d.rectangle([x0 + gw * 0.05, top + 170 * s, x1 - gw * 0.05, top + 200 * s], fill=col)

    # 子どもの影
    if 0 <= li and t < T_STOP + 0.25:
        zf = 9.0 / (1 + li * 0.9)   # 行ごとに「ふっと」近づく
        s = f / zf
        fx_ = W / 2 + (li % 2 * 2 - 1) * 18 * s
        by = hz + 330 * s
        hh = 300 * s
        sway = math.sin(t * 2.1) * 2 * s
        body = [(fx_ - 60 * s + sway, by), (fx_ + 60 * s + sway, by),
                (fx_ + 34 * s, by - hh * 0.62), (fx_ - 34 * s, by - hh * 0.62)]
        d.polygon(body, fill=(4, 3, 3), outline=(110, 40, 36))
        hr = 40 * s
        hy = by - hh * 0.62 - hr * 0.9
        d.rounded_rectangle([fx_ - hr * 1.05, hy - hr, fx_ + hr * 1.05, hy + hr * 1.15], radius=hr * 0.7, fill=(4, 3, 3), outline=(110, 40, 36), width=max(1, int(s * 2)))
        if li >= 4:  # 目が光る
            for ss in (-1, 1):
                ex = fx_ + ss * hr * 0.38
                r = max(1.5, hr * 0.08)
                d.ellipse([ex - r, hy + hr * 0.2 - r, ex + r, hy + hr * 0.2 + r], fill=(230, 220, 210))
        if li == 5:  # 手招き
            ay = by - hh * 0.5 + math.sin(t * 9) * 12 * s
            d.line([(fx_ + 30 * s, by - hh * 0.5), (fx_ + 80 * s, ay - 40 * s)], fill=(4, 3, 3), width=max(2, int(14 * s)))
    return img


def post(arr, t, intensity):
    """粒子・ビネット・色ずれ・ちらつき."""
    flick = 1 - 0.08 * (rng.random() < 0.15) - 0.03 * math.sin(t * 50)
    arr = arr * VIGNETTE * flick
    if intensity > 0:
        sh = int(4 + 18 * intensity)
        arr[..., 0] = np.roll(arr[..., 0], sh, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -sh, axis=1)
    grain = rng.normal(0, 9 + 10 * intensity, (H // 2, W // 2, 1)).astype(np.float32)
    grain = np.repeat(np.repeat(grain, 2, 0), 2, 1)
    arr = arr * SCAN + grain
    return arr


def render_frame(fi):
    t = fi / FPS
    li = line_index(t)

    # ---- 顔（ジャンプスケア）
    if T_SCARE <= t < T_SCARE_END:
        p = (t - T_SCARE) / (T_SCARE_END - T_SCARE)
        zoom = 1.0 + 0.35 * p + 0.05 * math.sin(t * 60)
        img = Image.fromarray(FACE.astype(np.uint8))
        nw, nh = int(W * zoom), int(H * zoom)
        img = img.resize((nw, nh))
        ox = (nw - W) // 2 + int(rng.uniform(-40, 40) * (1 - p))
        oy = (nh - H) // 2 + int(rng.uniform(-40, 40) * (1 - p))
        img = img.crop((ox, oy, ox + W, oy + H))
        d = ImageDraw.Draw(img)
        msg = "みぃつけた"
        bb = d.textbbox((0, 0), msg, font=F_SCARE)
        tw = bb[2] - bb[0]
        for k in range(3):
            d.text(((W - tw) / 2 + rng.uniform(-12, 12), 1450 + rng.uniform(-10, 10)), msg, font=F_SCARE,
                   fill=(170 + 40 * k, 0, 0))
        arr = np.asarray(img).astype(np.float32)
        if fi % 4 < 1:   # ネガ反転フラッシュ
            arr = 255 - arr
        arr[..., 0] *= 1.25
        arr[..., 1:] *= 0.75
        arr *= max(0.0, 1 - max(0, p - 0.8) * 5)
        arr = post(arr, t, 1.0)
        return np.clip(arr, 0, 255).astype(np.uint8)

    # ---- エンディング
    if t >= T_SCARE_END:
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        if t >= T_END_TEXT:
            a = min(1, (t - T_END_TEXT) / 1.0)
            c = (int(200 * a), int(190 * a), int(180 * a))
            vtext(d, W / 2 + 70, 520, "つぎの　おには", F_END, c)
            vtext(d, W / 2 - 70, 760, "あなた", F_END, (int(170 * a), 0, 0))
        arr = post(np.asarray(img).astype(np.float32), t, 0)
        return np.clip(arr, 0, 255).astype(np.uint8)

    # ---- 通常シーン
    img = draw_scene(t, li)
    d = ImageDraw.Draw(img)

    # タイトル
    if t < T0 + 0.4:
        a = min(1, t / 0.8) * min(1, (T0 + 0.4 - t) / 0.6)
        vtext(d, W / 2, 380, "かぞえうた", F_TITLE, (int(200 * a), int(30 * a), int(30 * a)), step=150)
        d.text((W / 2 - 110, 1700), "※ 音量注意", font=F_SMALL, fill=(int(150 * a),) * 3)

    # 歌詞（縦書き、音に合わせて1文字ずつ）
    if 0 <= li and t < T_STOP + 1.0:
        text = LYRICS[li]
        lt = t - (T0 + li * LINE)
        chars = [c for c in text if c != "　"]
        shown = min(len(chars), int(lt / (LINE * 0.9) * len(chars)) + 1)
        out, cnt = "", 0
        for c in text:
            if c == "　":
                out += c
                continue
            if cnt >= shown:
                break
            out += c
            cnt += 1
        fade = 1.0 if li < N_LINES - 1 else max(0.0, 1 - (t - T_STOP) / 1.0)
        jit = 0 if li < 4 else (li - 3) * 1.5
        col = (int(225 * fade), int(215 * fade), int(205 * fade)) if li < 5 else (int(220 * fade), int(60 * fade), int(50 * fade))
        vtext(d, W - 150, 260, out, F_LYRIC, col, jitter=jit)

    # 「うしろ」
    if T_WHISPER <= t < T_SCARE:
        a = min(1, (t - T_WHISPER) / 0.8)
        vtext(d, 150, 700, "うしろ", font(MINCHO, 96), (int(255 * a), int(40 * a), int(40 * a)), jitter=3)

    arr = np.asarray(img).astype(np.float32)

    # 行が変わる瞬間に暗転（「目を離したすきに近づく」）
    if li >= 1:
        lt = t - (T0 + li * LINE)
        if 0 <= lt < 0.07:
            arr *= 0.08
    # 歌が止まった後は暗く、静かに
    if t >= T_STOP:
        arr *= max(0.55, 1 - (t - T_STOP) * 0.4)
    intensity = 0.0 if li < 3 else min(1.0, (t - (T0 + 3 * LINE)) / (T_SCARE - (T0 + 3 * LINE))) * 0.3
    arr = post(arr, t, intensity)
    return np.clip(arr, 0, 255).astype(np.uint8)


def main():
    work = HERE / ".build"
    work.mkdir(exist_ok=True)
    wav_path = work / "audio.wav"
    print("audio ...", flush=True)
    audio = make_audio()
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(audio.tobytes())

    print("video ...", flush=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav_path),
           "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 60 == 0:
            print(f"  {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("done:", OUT)


if __name__ == "__main__":
    main()
