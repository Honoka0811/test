# -*- coding: utf-8 -*-
"""BGM と効果音をプログラムで合成し、ナレーションとダッキングしてミックスする(外部音源不要・権利フリー)。
BGM: 100BPM / Am-F-C-G。パッド + マリンバ風アルペジオ + 柔らかいキック/ハイハット。
「そして、あなたの一生は…」で音楽を止め、「0.5秒」で一気に戻す。
使い方: python3 bgm.py   (output/narration.wav と output/timings.json が必要)
出力: output/bgm.wav, output/mix.wav
"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
BPM = 100
BEAT = 60 / BPM
BAR = BEAT * 4
PROG = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
ROOT = [45, 41, 48, 43]
rng = np.random.default_rng(3)

def midi(n): return 440 * 2 ** ((n - 69) / 12)
def add(buf, t, sig, g=1.0):
    s = int(t * SR); e = min(len(buf), s + len(sig))
    if 0 <= s < e: buf[s:e] += sig[:e - s] * g
def env(n, a, r):
    e = np.ones(n, np.float32); na, nr = min(int(a * SR), n), min(int(r * SR), n)
    e[:na] = np.linspace(0, 1, na); e[n - nr:] = np.linspace(1, 0, nr); return e

def pad(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n, np.float32)
    for det in (-0.005, 0, 0.005):
        for h in range(1, 6):
            x += np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6)) / h ** 1.8
    return x * env(n, 0.6, 0.8)
def marimba(f, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.03)) * np.exp(-t / 0.22)).astype(np.float32)
def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 45 + 90 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)
def hat():
    n = int(0.06 * SR); x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(8) / 8, 'same')
    return x * np.exp(-np.arange(n) / SR / 0.015)
def bell(f, dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * r * t) * np.exp(-t / (0.5 / r)) * g for r, g in ((1, 1), (2.76, .4), (5.4, .2))).astype(np.float32)
def whoosh(dur=0.5):
    n = int(dur * SR); x = rng.standard_normal(n).astype(np.float32)
    lp = np.convolve(x, np.ones(24) / 24, 'same')
    return lp * np.sin(np.linspace(0, np.pi, n)) ** 2
def boom(dur=1.8):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 32 + 70 * np.exp(-t / 0.15)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.6)
    noise = np.convolve(rng.standard_normal(n), np.ones(60) / 60, 'same') * np.exp(-t / 0.25) * 3
    return (body + noise).astype(np.float32)
def tick():
    n = int(0.03 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.006)).astype(np.float32)
def reverb(x, mix=0.25):
    def comb(x, d, g):
        y = x.copy()
        for s in range(d, len(y), d):
            e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
        return y
    wet = sum(comb(x, d, g) for d, g in ((1553, .7), (1877, .68), (2251, .66), (2903, .6))) / 4
    return (1 - mix) * x + mix * wet

def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
def wr(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

tm = json.load(open(os.path.join(OUT, 'timings.json')))
cue = {c['id']: c for c in tm['cues']}
TOTAL = tm['duration']; N = int(TOTAL * SR) + 1
STOP, RESUME = cue['you_q']['start'] - 0.1, cue['you']['start']

pads, arp, drums = (np.zeros(N, np.float32) for _ in range(3))
b = 0
while b * BAR < TOTAL:
    t0 = b * BAR; ch = PROG[b % 4]
    for m in ch: add(pads, t0, pad(midi(m), BAR + 0.8), 0.5)
    add(pads, t0, pad(midi(ROOT[b % 4] - 12), BAR + 0.8), 0.8)
    for k in range(8):  # 8分音符のアルペジオ
        m = ch[[0, 1, 2, 1, 0, 2, 1, 2][k]] + 12 + (12 if k in (3, 7) and b % 2 else 0)
        add(arp, t0 + k * BEAT / 2, marimba(midi(m)), 0.9 if k % 2 == 0 else 0.6)
    if t0 >= cue['birth']['start'] - 0.1:   # フック後からビートを入れる
        for k in range(4):
            add(drums, t0 + k * BEAT, kick(), 1.0 if k in (0, 2) else 0.55)
            add(drums, t0 + k * BEAT + BEAT / 2, hat(), 0.35)
    b += 1

music = 0.45 * norm(reverb(pads, 0.3)) + 0.4 * norm(reverb(arp, 0.3)) + 0.55 * norm(drums)
# 「あなたの一生は…」で止めて、0.5秒で戻す
t = np.arange(N) / SR
g = np.ones(N, np.float32)
g[(t > STOP) & (t < RESUME)] = 0
fo = (t >= STOP - 0.4) & (t <= STOP); g[fo] = np.linspace(1, 0, fo.sum())
music *= g
music *= env(N, 0.3, 2.0)

# 効果音
sfx = np.zeros(N, np.float32)
for c in tm['cues']:
    if c['id'] in ('birth', 'life', 'cambr', 'dino', 'human', 'agri'):
        add(sfx, c['start'] - 0.25, whoosh(), 0.25)
        add(sfx, c['start'] + 0.15, bell(midi(84)), 0.35)
add(sfx, cue['dino']['start'] + 3.2 + 0.85, boom(), 0.6)          # 隕石
add(sfx, cue['human_q']['start'], bell(midi(79)), 0.4)
for i in range(int((cue['you_q']['end'] - cue['agri']['start']) / 1.0)):  # 時計の秒針
    add(sfx, cue['agri']['start'] + i, tick(), 0.25)
add(sfx, RESUME, boom(), 0.9)                                      # 0.5秒!
add(sfx, RESUME, bell(midi(88), 2.5), 0.5)

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
# ダッキング
hop = SR // 20
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, 1))
e = np.zeros_like(rms)
for i, v in enumerate(rms): e[i] = max(v, (e[i - 1] if i else 0) * 0.9)
e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop))
duck = 0.42 - 0.24 * np.clip(e / 0.1, 0, 1)
duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), 'same')
music_out = music * duck
wr(os.path.join(OUT, 'bgm.wav'), norm(music) * 0.9)
mixed = voice + music_out + 0.5 * sfx
mixed /= max(1.0, np.max(np.abs(mixed)) / 0.95)
wr(os.path.join(OUT, 'mix.wav'), mixed)
print(f'wrote output/bgm.wav, output/mix.wav ({TOTAL:.1f}s)')
