# -*- coding: utf-8 -*-
"""BGM(和風トラップ/120BPM)と効果音を numpy で合成し、ナレーションとミックスする。外部音源なし・権利フリー。
timeline.json(narrate.py が生成)に合わせて、
  - フック中は箏リフだけ → ライザー → タイトルで「ドロップ」(ビート全開)
  - 各ランク発表で和太鼓のインパクト、場面転換でウーッシュ、数字の決め台詞でキラッ音
  - ナレーション中は BGM を自動で下げる(ダッキング)
出力: output/bgm.wav, output/sfx.wav, output/mix.wav(ステレオ)
"""
import os, json, wave
import numpy as np
from scipy.signal import lfilter, butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
BPM = 120; BEAT = 60 / BPM; BAR = BEAT * 4; S16 = BEAT / 4
rng = np.random.default_rng(11)

TL = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))
TOTAL = TL['total']
SC = {s['id']: s for s in TL['scenes']}
N = int(TOTAL * SR)
DROP = SC['title']['t0']

def midi(n): return 440 * 2 ** ((n - 69) / 12)
def add(buf, t, sig, g=1.0):
    s = int(round(t * SR))
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += g * sig[:e - s]
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)
def noise(sec): return rng.standard_normal(int(sec * SR)).astype(np.float32)
def tt(sec): return np.arange(int(sec * SR)) / SR

# ---------------- 楽器 ----------------
def koto(f, dur=1.4, bright=0.6):
    """Karplus-Strong による箏風の撥弦"""
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = (rng.uniform(-1, 1, p) * 1.0).astype(np.float32)
    out = np.zeros(n, dtype=np.float32)
    # 周期 p のディレイ + 平均化フィルタ(ブロック処理)
    cur = buf.copy(); i = 0
    decay = 0.996
    while i < n:
        k = min(p, n - i); out[i:i + k] = cur[:k]
        cur = (decay * (bright * cur + (1 - bright) * np.roll(cur, 1))).astype(np.float32); i += p
    t = tt(dur)[:n]
    att = np.minimum(1, t / 0.002)
    tone = out * att * np.exp(-t / 0.9)
    return (tone + 0.25 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.4)).astype(np.float32)

def kick(dur=0.45):
    t = tt(dur); f = 45 + 110 * np.exp(-t / 0.045)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)
    x += 0.3 * hp(noise(dur), 2000) * np.exp(-t / 0.004)
    return np.tanh(1.6 * x).astype(np.float32)

def clap(dur=0.3):
    t = tt(dur); x = bp(noise(dur), 900, 5000)
    env = np.exp(-t / 0.09)
    for d in (0.0, 0.011, 0.022):
        env += 0.6 * np.exp(-np.maximum(t - d, 0) / 0.006) * (t >= d)
    return (x * env * 0.5).astype(np.float32)

def hat(dur=0.05, open_=False):
    d = 0.22 if open_ else dur; t = tt(d)
    return (hp(noise(d), 7000) * np.exp(-t / (0.08 if open_ else 0.015))).astype(np.float32)

def sub(f, dur):
    t = tt(dur); x = np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t)
    env = np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.05)
    return np.tanh(1.3 * x * env).astype(np.float32)

def pad(notes, dur):
    t = tt(dur); x = np.zeros_like(t)
    for m in notes:
        for det in (-0.006, 0, 0.006):
            ph = rng.uniform(0, 6.3)
            for h in range(1, 6):
                x += np.sin(2 * np.pi * midi(m) * (1 + det) * h * t + ph) / h ** 1.4
    env = np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4)
    return lp(x * env, 2500).astype(np.float32)

def taiko(dur=1.4):
    t = tt(dur); f = 50 + 70 * np.exp(-t / 0.07)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    skin = lp(noise(dur), 1500) * np.exp(-t / 0.03)
    return np.tanh(2.0 * (body + 0.5 * skin)).astype(np.float32)

def whoosh(dur=0.55, up=True):
    t = tt(dur); x = noise(dur); y = np.zeros_like(x)
    # 帯域を時間とともにスイープ(ブロックごとにフィルタ)
    blk = 1024
    for i in range(0, len(x), blk):
        p = i / len(x); fc = 300 + (5000 if up else 2500) * (p if up else 1 - p)
        y[i:i + blk] = bp(x[max(0, i - 2048):i + blk], fc * 0.6, min(fc * 1.6, 20000))[-len(x[i:i + blk]):]
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (y * env).astype(np.float32)

def riser(dur):
    t = tt(dur); f = 200 * (8 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    nz = hp(noise(dur), 2000) * 0.6
    return ((tone + nz) * (t / dur) ** 2).astype(np.float32)

def ding(f=1568):
    dur = 1.2; t = tt(dur)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for a, r, d in ((1, 1, 0.6), (0.5, 2.76, 0.25), (0.3, 5.4, 0.1)))
    return (x * np.minimum(1, t / 0.002)).astype(np.float32)

def reverb(x, mix=0.25):
    wet = np.zeros_like(x)
    for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (2671, 0.64)):
        y = x.copy()
        for s in range(d, len(y), d):
            e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
        wet += y
    return (1 - mix) * x + mix * lp(wet / 4, 6000)

# ---------------- アレンジ ----------------
# 平調子風(D E F A Bb)。2 小節のリフ: (16分位置, MIDI)
RIFF = [(0, 74), (3, 77), (4, 76), (6, 74), (8, 81), (10, 77), (12, 76), (14, 74),
        (16, 70), (19, 74), (20, 76), (22, 77), (24, 74), (27, 69), (28, 70), (30, 69)]
RIFF_B = [(0, 81), (2, 82), (3, 81), (6, 77), (8, 76), (10, 77), (12, 81), (14, 86),
          (16, 82), (18, 81), (20, 77), (22, 76), (24, 74), (26, 76), (28, 77), (30, 81)]
ROOTS = [38, 34, 41, 33]            # D, Bb, F, A(1 小節ずつ)
CHORDS = [[62, 65, 69], [58, 62, 65], [60, 65, 69], [61, 64, 69]]

koto_b = np.zeros(N, np.float32); drums = np.zeros(N, np.float32)
bass = np.zeros(N, np.float32); padb = np.zeros(N, np.float32)
sfx = np.zeros(N, np.float32)
kcache = {}
def kt(m):
    if m not in kcache: kcache[m] = koto(midi(m))
    return kcache[m]
KICK, CLAP, HAT, OHAT = kick(), clap(), hat(), hat(open_=True)

OUTRO_STOP = SC['outro']['t1'] - 1.2
INARI = SC['inari']['t0']
first_bar = -int(np.ceil(DROP / BAR))
last_bar = int(np.ceil((TOTAL - DROP) / BAR))
for b in range(first_bar, last_bar + 1):
    t0 = DROP + b * BAR
    hi = t0 >= INARI - 0.01           # 1 位から盛り上げ
    riff = RIFF_B if (hi and (b % 4) >= 2) else RIFF
    half = (b % 2) * 16
    for pos, m in riff:
        if half <= pos < half + 16:
            t = t0 + (pos - half) * S16
            if t < TOTAL: add(koto_b, t, kt(m), 0.9 if pos % 4 == 0 else 0.65)
    if b < 0:  # イントロ: 箏 + パッドのみ
        add(padb, t0, pad(CHORDS[b % 4], BAR + 0.3), 0.5)
        continue
    if t0 >= OUTRO_STOP:   # 最後: ブレイク
        add(padb, t0, pad(CHORDS[0], BAR + 0.3), 0.6)
        continue
    add(padb, t0, pad(CHORDS[b % 4], BAR + 0.3), 0.45)
    root = ROOTS[b % 4]
    # トラップ系キック/ベース
    for k in (0, 6, 10) if b % 2 == 0 else (0, 3, 10, 14):
        add(drums, t0 + k * S16, KICK, 1.0)
        add(bass, t0 + k * S16, sub(midi(root), S16 * (4 if k != 14 else 2)), 0.8)
    for k in (4, 12):
        add(drums, t0 + k * S16, CLAP, 0.8)
    for k in range(16):
        roll = hi and b % 2 == 1 and k >= 12
        if roll:   # ハイハット・ロール(32分)
            add(drums, t0 + k * S16, HAT, 0.2); add(drums, t0 + (k + 0.5) * S16, HAT, 0.16)
        elif k % 2 == 0 or hi:
            add(drums, t0 + k * S16, HAT, 0.22 if k % 4 == 0 else 0.13)
    if b % 4 == 3: add(drums, t0 + 14 * S16, OHAT, 0.3)

# イントロのリフはこもらせ、ドロップで開く
cut = int(DROP * SR)
koto_b[:cut] = lp(koto_b[:cut], 1400)

# ---------------- 効果音 ----------------
add(sfx, 0.0, taiko(), 0.9)                                   # 冒頭のつかみ
add(sfx, DROP - 1.9, lp(riser(1.9), 6000), 0.25)                          # ドロップ前
add(sfx, DROP, taiko(), 1.0); add(sfx, DROP, whoosh(0.5, False), 0.4)
for sid in ('kiyomizu', 'kinkaku', 'inari', 'outro'):
    add(sfx, SC[sid]['t0'] - 0.25, whoosh(0.55), 0.55)          # 場面転換
for c in TL['caps']:
    if c['text'].startswith('第'):
        add(sfx, c['t0'] + 0.05, taiko(), 0.9)                 # ランク発表
    if any(k in c['text'] for k in ('234件', '85%', '20万枚', '1万基', '全焼')):
        add(sfx, c['t1'] - 0.55, ding(1760 if '%' in c['text'] else 1568), 0.35)

# ---------------- ミックス ----------------
def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
music = 0.55 * norm(reverb(koto_b, 0.3)) + 0.75 * norm(drums) + 0.55 * norm(bass) + 0.22 * norm(reverb(padb, 0.3))
music = np.tanh(1.2 * norm(music)) * 0.9
music[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
sfx = reverb(sfx, 0.15)

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    nar = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
nar = np.pad(nar, (0, max(0, N - len(nar))))[:N]
# ダッキング
hop = SR // 50
rms = np.sqrt(np.mean(np.pad(nar, (0, -len(nar) % hop)).reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.94)
env = np.repeat(np.clip(env / 0.06, 0, 1), hop)[:N]
k = SR // 20; env = np.convolve(env, np.ones(k) / k, 'same')
gain = 0.42 - (0.42 - 0.17) * env
mono_mix = nar * 1.0 + music * gain + sfx * 0.45 / (np.max(np.abs(sfx)) + 1e-9)
# 簡易ステレオ化: BGM の箏とハイハットを少し左右に広げる(ナレーションは中央)
side = 0.12 * gain * (norm(koto_b) - np.roll(norm(drums), 240)) * 0.5
L, R = mono_mix + side, mono_mix - side
st = np.stack([L, R], 1); st /= max(1.0, np.max(np.abs(st)) / 0.97)

def wr(path, x):
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x
    ch = 1 if x.ndim == 1 else x.shape[1]
    with wave.open(path, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
wr(os.path.join(OUT, 'bgm.wav'), music)
wr(os.path.join(OUT, 'sfx.wav'), norm(sfx) * 0.8)
wr(os.path.join(OUT, 'mix.wav'), st)
print('wrote output/bgm.wav sfx.wav mix.wav', f'{TOTAL:.2f}s')
