# -*- coding: utf-8 -*-
"""
日本の絶景TOP10 ショート動画ビルダー（1080x1920 / 30fps）

必要: VOICEVOX ENGINE (http://localhost:50021), ffmpeg, Pillow, numpy
  docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
  python3 build.py

photos/ に写真（script.py のファイル名）を置くと、イメージイラストの代わりに使われます。
"""
import hashlib
import json
import math
import os
import random
import subprocess
import urllib.parse
import urllib.request
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import script as S
from scenes import SCENES

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
CACHE = os.path.join(ROOT, ".cache")
PHOTOS = os.path.join(ROOT, "photos")
VV = os.environ.get("VOICEVOX_URL", "http://localhost:50021")
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
VW, VH, FPS, SR = 1080, 1920, 30, 44100
os.makedirs(OUT, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

GOLD = (255, 205, 60)
WHITE = (255, 255, 255)


# ---------------------------------------------------------------- 音声合成
def tts(text, speaker, speed=1.12):
    key = f"{speaker}_{speed}_{hashlib.md5(text.encode()).hexdigest()[:12]}.wav"
    path = os.path.join(CACHE, key)
    if not os.path.exists(path):
        q = urllib.parse.urlencode({"text": text, "speaker": speaker})
        req = urllib.request.Request(f"{VV}/audio_query?{q}", method="POST")
        query = json.loads(urllib.request.urlopen(req).read())
        query.update(speedScale=speed, intonationScale=1.25, volumeScale=1.2,
                     outputSamplingRate=SR, prePhonemeLength=0.05, postPhonemeLength=0.1)
        req = urllib.request.Request(f"{VV}/synthesis?speaker={speaker}", data=json.dumps(query).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        open(path, "wb").write(urllib.request.urlopen(req).read())
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
    return a


# ---------------------------------------------------------------- タイムライン
def build_timeline():
    segs = []
    hook_a = tts(S.HOOK["narration"], S.HOOK["speaker"], 1.2)
    segs.append(dict(kind="hook", audio=hook_a, dur=max(len(hook_a) / SR + 0.4, 3.6), voice_at=0.15))
    for sp in S.SPOTS:
        rank, photo, name, pref, season, narr, cap, scene = sp
        if rank == 1:
            a = tts(S.SUSPENSE["narration"], S.SUSPENSE["speaker"], 0.95)
            segs.append(dict(kind="suspense", audio=a, dur=len(a) / SR + 0.9, voice_at=0.2))
        a = tts(narr, S.SPOT_SPEAKER, 1.22 if rank != 1 else 1.08)
        segs.append(dict(kind="spot", rank=rank, photo=photo, name=name, pref=pref, season=season,
                         cap=cap, scene=scene, audio=a, dur=len(a) / SR + (0.4 if rank != 1 else 1.2),
                         voice_at=0.3))
    a = tts(S.OUTRO["narration"], S.OUTRO["speaker"], 1.15)
    segs.append(dict(kind="outro", audio=a, dur=len(a) / SR + 1.2, voice_at=0.3))
    t = 0
    for s in segs:
        s["start"] = t
        t += s["dur"]
    return segs, t


# ---------------------------------------------------------------- BGM・効果音（オリジナル合成）
def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def kick(n=int(0.35 * SR)):
    t = np.arange(n) / SR
    f = 50 + 120 * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.9


def snare(n=int(0.25 * SR), rng=np.random.default_rng(1)):
    t = np.arange(n) / SR
    return (rng.normal(0, 1, n) * 0.5 + np.sin(2 * np.pi * 190 * t) * 0.5) * np.exp(-t * 18) * 0.5


def hat(n=int(0.06 * SR), rng=np.random.default_rng(2)):
    x = rng.normal(0, 1, n)
    x = np.diff(np.concatenate([[0], x]))
    return x * np.exp(-np.arange(n) / SR * 70) * 0.12


def saw(freq, n):
    t = np.arange(n) / SR
    return 2 * ((t * freq) % 1) - 1


def lowpass(x, cutoff):
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # 小さな配列にのみ使用
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def note(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def make_bgm(total, drop_ranges):
    """124BPM のエピック・ポップ。drop_ranges の区間は静か（ため）にする"""
    bpm = 124
    beat = 60 / bpm
    n = int(total * SR) + SR
    mix = np.zeros(n)
    pad = np.zeros(n)
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]  # Am F C G
    k, sn, h = kick(), snare(), hat()
    bar = beat * 4
    nb = int(total / bar) + 2
    rng = np.random.default_rng(3)
    for b in range(nb):
        root, chord = prog[b % 4]
        t0 = b * bar
        i0 = int(t0 * SR)
        L = int(bar * SR)
        if i0 >= n:
            break
        seg = slice(i0, min(n, i0 + L))
        m = seg.stop - seg.start
        # パッド
        p = sum(saw(note(c), m) + saw(note(c) * 1.006, m) for c in chord) / 6
        pad[seg] += p * 0.18
        # ベース（8分）
        for e in range(8):
            j = i0 + int(e * beat / 2 * SR)
            ln = int(beat / 2 * SR * 0.9)
            if j + ln > n:
                continue
            bs = np.sign(np.sin(2 * np.pi * note(root - 12) * np.arange(ln) / SR)) * 0.5
            mix[j:j + ln] += bs * env(ln, 0.003, 0.12) * 0.32
        # アルペジオ
        arp = chord + [chord[0] + 12, chord[1] + 12]
        for e in range(16):
            j = i0 + int(e * beat / 4 * SR)
            ln = int(0.18 * SR)
            if j + ln > n:
                continue
            f = note(arp[(e * 3) % len(arp)] + 12)
            tt = np.arange(ln) / SR
            mix[j:j + ln] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * env(ln, 0.002, 0.08) * 0.12
        # ドラム
        for q in range(4):
            j = i0 + int(q * beat * SR)
            if j + len(k) < n:
                mix[j:j + len(k)] += k
            if q in (1, 3) and j + len(sn) < n:
                mix[j:j + len(sn)] += sn
            for e in range(2):
                jj = j + int(e * beat / 2 * SR)
                if jj + len(h) < n:
                    mix[jj:jj + len(h)] += h * (1.4 if e else 0.8)
    # パッドを柔らかく（簡易ローパス：移動平均）
    kern = np.ones(24) / 24
    pad = np.convolve(pad, kern, mode="same")
    out = mix + pad
    # 「ため」区間はリズムを抜いてパッドのみ
    for a, b in drop_ranges:
        ia, ib = int(a * SR), int(b * SR)
        fade = np.ones(ib - ia)
        f = min(int(0.05 * SR), len(fade) // 2)
        out[ia:ib] = out[ia:ib] * 0 + pad[ia:ib] * 0.6
    return out[:int(total * SR)]


def add(buf, x, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m] * gain


def make_audio(segs, total):
    n = int(total * SR)
    voice = np.zeros(n)
    drops = []
    for s in segs:
        add(voice, s["audio"], s["start"] + s["voice_at"])
        if s["kind"] == "suspense":
            drops.append((s["start"], s["start"] + s["dur"]))
    bgm = make_bgm(total, drops)
    # ダッキング（ナレーション中はBGMを下げる）
    ve = np.convolve(np.abs(voice), np.ones(4410) / 4410, mode="same")
    duck = 1 - 0.55 * np.clip(ve / 0.03, 0, 1)
    duck = np.convolve(duck, np.ones(2205) / 2205, mode="same")
    fade = np.ones(n)
    fl = int(1.2 * SR)
    fade[-fl:] = np.linspace(1, 0, fl)
    mix = voice * 1.0 + bgm * 0.32 * duck * fade
    mix /= max(1e-6, np.max(np.abs(mix))) / 0.95
    path = os.path.join(CACHE, "mix.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return path


# ---------------------------------------------------------------- 画像
def font(size):
    return ImageFont.truetype(FONT, size)


def text_img(text, size, fill=WHITE, stroke=10, stroke_fill=(0, 0, 0), spacing=12, shadow=True):
    f = font(size)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    box = d.multiline_textbbox((0, 0), text, font=f, stroke_width=stroke, spacing=spacing, align="center")
    w, h = int(box[2] - box[0] + 40), int(box[3] - box[1] + 40)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    org = (20 - box[0], 20 - box[1])
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text((org[0] + 6, org[1] + 8), text, font=f, fill=(0, 0, 0, 170),
                                          stroke_width=stroke, stroke_fill=(0, 0, 0, 170), spacing=spacing, align="center")
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    dd.multiline_text(org, text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill,
                      spacing=spacing, align="center")
    return img


def chip(text, size, bg, fg=WHITE, pad=(28, 14)):
    f = font(size)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    b = d.textbbox((0, 0), text, font=f)
    w, h = int(b[2] - b[0] + pad[0] * 2), int(b[3] - b[1] + pad[1] * 2)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    dd.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg)
    dd.text((pad[0] - b[0], pad[1] - b[1]), text, font=f, fill=fg)
    return img


def rank_badge(rank):
    big = rank == 1
    t1 = text_img("第", 90 if not big else 110, GOLD, 9)
    t2 = text_img(str(rank), 260 if not big else 330, GOLD, 14)
    t3 = text_img("位", 90 if not big else 110, GOLD, 9)
    w = t1.width + t2.width + t3.width - 60
    h = t2.height
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.alpha_composite(t1, (0, h - t1.height - 30))
    img.alpha_composite(t2, (t1.width - 30, 0))
    img.alpha_composite(t3, (t1.width + t2.width - 60, h - t3.height - 30))
    return img


def load_bg(spot):
    p = os.path.join(PHOTOS, spot[1])
    cache = os.path.join(CACHE, f"bg_{spot[7]}.png")
    if os.path.exists(p):
        im = Image.open(p).convert("RGB")
        r = max(1350 / im.width, 2400 / im.height)
        im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
        l, t = (im.width - 1350) // 2, (im.height - 2400) // 2
        return im.crop((l, t, l + 1350, t + 2400)), True
    if not os.path.exists(cache):
        SCENES[spot[7]]().save(cache)
    return Image.open(cache).convert("RGB"), False


def ease_out(x):
    x = min(1, max(0, x))
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = min(1, max(0, x))
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def kenburns(bg, t, dur, seed, punch=True):
    z = 1.0 + 0.10 * (t / dur)
    if punch:
        z += 0.05 * (1 - ease_out(t / 0.5))
    rnd = random.Random(seed)
    dx, dy = rnd.uniform(-1, 1), rnd.uniform(-1, 1)
    cw, ch = 1350 / (1.25 * z) * 1.0, 2400 / (1.25 * z)
    cx = 675 + dx * (1350 - cw) / 2 * (t / dur)
    cy = 1200 + dy * (2400 - ch) / 2 * (t / dur)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return bg.transform((VW, VH), Image.EXTENT, box, Image.BILINEAR)


SHADE = None


def shade():
    global SHADE
    if SHADE is None:
        a = np.zeros((VH, VW), np.float32)
        y = np.arange(VH)[:, None]
        a += np.clip(1 - y / 650, 0, 1) ** 1.5 * 170
        a += np.clip((y - 1150) / 770, 0, 1) ** 1.3 * 200
        img = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
        img.putalpha(Image.fromarray(np.broadcast_to(a, (VH, VW)).astype(np.uint8)))
        SHADE = img
    return SHADE


def paste_scaled(frame, img, center, scale, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    w, h = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    im = img.resize((w, h), Image.BILINEAR)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im.putalpha(a)
    frame.alpha_composite(im, (int(center[0] - w / 2), int(center[1] - h / 2)))


def progress(frame, current):
    """上部の進捗バー（10→1 のカウントダウン）"""
    d = ImageDraw.Draw(frame)
    n = 10
    gap, x0, w_all = 8, 60, VW - 120
    w = (w_all - gap * (n - 1)) / n
    for i in range(n):
        rank = 10 - i
        x = x0 + i * (w + gap)
        col = GOLD + (255,) if current is not None and rank >= current else (255, 255, 255, 90)
        d.rounded_rectangle((x, 70, x + w, 82), radius=6, fill=col)


def credit_layer():
    return text_img("VOICEVOX:青山龍星", 30, (255, 255, 255), 4, shadow=False)


# ---------------------------------------------------------------- 各シーン描画
class Renderer:
    def __init__(self, segs):
        self.segs = segs
        self.bgs = {}
        self.illustrated = {}
        for sp in S.SPOTS:
            bg, real = load_bg(sp)
            self.bgs[sp[0]] = bg
            self.illustrated[sp[0]] = not real
        self.credit = credit_layer()
        cp = os.path.join(PHOTOS, "credits.json")
        credits = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
        self.photo_credit = {}
        for sp in S.SPOTS:
            c = credits.get(sp[1])
            if c and not self.illustrated[sp[0]]:
                self.photo_credit[sp[0]] = text_img("Photo: " + c, 24, WHITE, 3, shadow=False)
        self.img_note = text_img("※イメージ", 28, (255, 255, 255), 3, shadow=False)
        self.hook_titles = [text_img(S.HOOK["title"][0], 100, WHITE, 12),
                            text_img(S.HOOK["title"][1], 150, WHITE, 14),
                            text_img(S.HOOK["title"][2], 300, GOLD, 18)]
        self.cache = {}
        self.thumbs = {r: bg.resize((300, 533), Image.BILINEAR) for r, bg in self.bgs.items()}

    def spot_layers(self, s):
        r = s["rank"]
        if r not in self.cache:
            self.cache[r] = dict(
                badge=rank_badge(r),
                name=text_img(s["name"], 120 if len(s["name"]) <= 6 else 96, WHITE, 12),
                pref=chip(s["pref"], 46, (220, 40, 60, 235)),
                cap=text_img(s["cap"], 70, WHITE, 9, spacing=20),
                season=chip("見頃：" + s["season"], 42, (0, 0, 0, 160)),
            )
        return self.cache[r]

    def render_seg(self, s, lt):
        return getattr(self, "r_" + s["kind"])(s, lt)

    def frame(self, t):
        xf = 0.3  # クロスフェード秒数
        for i, s in enumerate(self.segs):
            if s["start"] <= t < s["start"] + s["dur"]:
                lt = t - s["start"]
                cur = self.render_seg(s, lt)
                if i > 0 and lt < xf:
                    p = self.segs[i - 1]
                    prev = self.render_seg(p, p["dur"] + lt)
                    cur = Image.blend(prev, cur, ease_out(lt / xf))
                return cur
        return self.r_outro(self.segs[-1], self.segs[-1]["dur"] - 0.01)

    def r_hook(self, s, t):
        order = [r for r in range(10, 0, -1)]
        cut = 0.45
        idx = min(int(t / cut), 9)
        if t > cut * 10:
            idx = 0  # 最後は1位（富士）を背景に
            bg = self.bgs[1]
            frame = kenburns(bg, t - cut * 10, s["dur"], 1, punch=False).convert("RGBA")
        else:
            r = order[idx]
            frame = kenburns(self.bgs[r], t % cut, cut * 3, r, punch=True).convert("RGBA")
        frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, 90)))
        frame.alpha_composite(shade())
        # タイトル（段階的に登場）
        ys = [700, 860, 1120]
        for i, ti in enumerate(self.hook_titles):
            st = 0.15 + i * 0.35
            if t < st:
                continue
            p = (t - st) / 0.35
            sc = ease_back(p) if i < 2 else (2.2 - 1.2 * ease_out(p))
            al = min(1, p * 3)
            shake = 0
            if i == 2 and p < 0.6:
                shake = math.sin(t * 90) * 14 * (1 - p / 0.6)
            paste_scaled(frame, ti, (VW / 2 + shake, ys[i]), sc, al)
        if t > 1.5:  # 「最後まで見てね」
            pulse = 1 + 0.05 * math.sin(t * 10)
            if not hasattr(self, "_hk"):
                self._hk = chip("第1位は最後に発表！", 54, (220, 40, 60, 240))
            paste_scaled(frame, self._hk, (VW / 2, 1420), pulse * ease_back((t - 1.5) / 0.3))
        self.common(frame, None, False)
        return frame

    def r_spot(self, s, t):
        r = s["rank"]
        L = self.spot_layers(s)
        frame = kenburns(self.bgs[r], t, s["dur"], r).convert("RGBA")
        frame.alpha_composite(shade())
        big = r == 1
        # 順位バッジ（ポップイン）
        p = t / 0.4
        sc = ease_back(p) * (1 + 0.03 * math.sin(t * 6))
        paste_scaled(frame, L["badge"], (VW / 2, 330 if not big else 360), sc, min(1, p * 2))
        # 県名チップ＋スポット名（左からスライド）
        p2 = ease_out((t - 0.18) / 0.35)
        if p2 > 0:
            off = (1 - p2) * -VW
            paste_scaled(frame, L["pref"], (VW / 2 + off, 1290), 1, p2)
            paste_scaled(frame, L["name"], (VW / 2 - off, 1420), 1, p2)
        # 字幕（下からフェード）
        p3 = ease_out((t - 0.45) / 0.35)
        if p3 > 0:
            paste_scaled(frame, L["cap"], (VW / 2, 1620 + (1 - p3) * 60), 1, p3)
        p4 = ease_out((t - 0.8) / 0.3)
        if p4 > 0:
            paste_scaled(frame, L["season"], (VW / 2, 1790), p4, p4)
        if big:
            self.confetti(frame, t)
        self.common(frame, r, self.illustrated[r])
        return frame

    def confetti(self, frame, t):
        d = ImageDraw.Draw(frame)
        rnd = random.Random(42)
        cols = [GOLD, (255, 120, 150), (120, 220, 255), (255, 255, 255)]
        for i in range(140):
            x0 = rnd.uniform(0, VW)
            sp = rnd.uniform(250, 600)
            st = rnd.uniform(0, 1.5)
            if t < st:
                continue
            y = -40 + (t - st) * sp
            x = x0 + math.sin((t - st) * rnd.uniform(2, 5) + i) * 40
            if y > VH:
                continue
            a = rnd.uniform(0, 6.28) + t * 6
            w = 14 * abs(math.cos(a)) + 3
            d.rectangle((x - w, y - 7, x + w, y + 7), fill=rnd.choice(cols) + (230,))

    def r_suspense(self, s, t):
        bg = self.bgs[1].filter(ImageFilter.GaussianBlur(40)) if "blurred1" not in self.cache else self.cache["blurred1"]
        self.cache["blurred1"] = bg
        frame = kenburns(bg, t, s["dur"], 7, punch=False).convert("RGBA")
        dark = int(150 + 80 * min(1, t / s["dur"]))
        frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, dark)))
        if "sus" not in self.cache:
            self.cache["sus"] = text_img("第1位は…", 150, GOLD, 14)
            self.cache["q"] = text_img("?", 420, WHITE, 16)
        sc = 1 + 0.1 * (t / s["dur"]) + 0.02 * math.sin(t * 25 * (t / s["dur"]))
        paste_scaled(frame, self.cache["q"], (VW / 2, 820), sc, min(1, t / 0.3) * 0.9)
        paste_scaled(frame, self.cache["sus"], (VW / 2, 1200), ease_back(t / 0.4))
        self.common(frame, 2, False)
        return frame

    def r_outro(self, s, t):
        frame = Image.new("RGBA", (VW, VH), (12, 16, 30, 255))
        # 2x5 グリッド
        for i, r in enumerate(range(1, 11)):
            col, row = i % 2, i // 2
            st = i * 0.06
            p = ease_out((t - st) / 0.35)
            if p <= 0:
                continue
            th = self.thumbs[r].resize((480, 280), Image.BILINEAR) if ("th", r) not in self.cache else self.cache[("th", r)]
            self.cache[("th", r)] = th
            x = 50 + col * 500 + 240
            y = 160 + row * 300 + 140 + (1 - p) * 80
            tile = th.convert("RGBA")
            if ("lab", r) not in self.cache:
                self.cache[("lab", r)] = text_img(f"{r}位", 60, GOLD if r == 1 else WHITE, 7, shadow=False)
            tile = tile.copy()
            tile.alpha_composite(self.cache[("lab", r)], (0, 0))
            paste_scaled(frame, tile, (x, y), 1, p)
        frame.alpha_composite(Image.new("RGBA", (VW, VH), (0, 0, 0, int(140 * ease_out((t - 0.8) / 0.4)))))
        if "cta" not in self.cache:
            self.cache["cta"] = text_img("行きたいのは何位？", 100, WHITE, 12)
            self.cache["cta2"] = chip("コメントで教えてね", 64, (220, 40, 60, 245))
            self.cache["cta3"] = chip("保存して旅の参考に！", 64, (255, 205, 60, 250), fg=(30, 30, 30))
        paste_scaled(frame, self.cache["cta"], (VW / 2, 820), ease_back((t - 0.6) / 0.4))
        paste_scaled(frame, self.cache["cta2"], (VW / 2, 1010), ease_back((t - 1.0) / 0.4) * (1 + 0.04 * math.sin(t * 8)))
        paste_scaled(frame, self.cache["cta3"], (VW / 2, 1150), ease_back((t - 1.6) / 0.4))
        self.common(frame, 0, False)
        return frame

    def common(self, frame, current, illustrated):
        progress(frame, current)
        frame.alpha_composite(self.credit, (VW - self.credit.width - 30, VH - self.credit.height - 30))
        if current in self.photo_credit and current != 0:
            c = self.photo_credit[current]
            frame.alpha_composite(c, (30, VH - c.height - 70))


def main():
    segs, total = build_timeline()
    print(f"total {total:.1f}s, {len(segs)} segments")
    audio = make_audio(segs, total)
    rnd = Renderer(segs)
    nframes = int(total * FPS)
    out = os.path.join(OUT, "japan_zekkei_top10.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}",
           "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(nframes):
        f = rnd.frame(i / FPS).convert("RGB")
        proc.stdin.write(f.tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{nframes}", flush=True)
    proc.stdin.close()
    proc.wait()
    # サムネイル（1位の見せ場）
    for s in segs:
        if s["kind"] == "spot" and s["rank"] == 1:
            rnd.frame(s["start"] + 2.0).convert("RGB").save(os.path.join(OUT, "thumbnail.jpg"), quality=92)
    print("done:", out)


if __name__ == "__main__":
    main()
