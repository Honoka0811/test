"""オリジナルBGMをnumpyで合成する（明るめのポップ、120BPM）。
usage: python3 bgm.py <seconds> <out.wav>
"""
import sys
import wave

import numpy as np

SR = 48000
BPM = 124
BEAT = 60 / BPM
dur = float(sys.argv[1])
out = sys.argv[2]
n = int(SR * (dur + 1))
L = np.zeros(n)
R = np.zeros(n)


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def env(length, a=0.005, d=0.25, s=0.0):
    t = np.arange(length) / SR
    e = np.minimum(t / a, 1.0) * (s + (1 - s) * np.exp(-t / d))
    rel = min(len(t), int(0.02 * SR))
    e[-rel:] *= np.linspace(1, 0, rel)
    return e


def add(buf, start, sig, gain):
    i = int(start * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig * gain


def pluck(freq, length):
    t = np.arange(int(length * SR)) / SR
    s = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t)
         + 0.15 * np.sin(2 * np.pi * 3 * freq * t))
    return s * env(len(t), d=0.18)


def bass(freq, length):
    t = np.arange(int(length * SR)) / SR
    s = np.tanh(2.2 * np.sin(2 * np.pi * freq * t))
    return s * env(len(t), a=0.004, d=0.35, s=0.3)


def pad(freqs, length):
    t = np.arange(int(length * SR)) / SR
    s = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.3 * t)) for f in freqs) / len(freqs)
    e = np.minimum(t / 0.3, 1) * np.minimum((length - t) / 0.3, 1)
    return s * e


rng = np.random.default_rng(7)


def kick():
    t = np.arange(int(0.25 * SR)) / SR
    f = 50 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12)


def hat():
    t = np.arange(int(0.05 * SR)) / SR
    x = rng.standard_normal(len(t))
    x = np.diff(x, prepend=0)
    return x * np.exp(-t * 90)


def clap():
    t = np.arange(int(0.15 * SR)) / SR
    x = rng.standard_normal(len(t))
    return x * np.exp(-t * 30) * (1 + 0.5 * np.sin(2 * np.pi * 90 * t))


# C - G - Am - F  (各1小節)
chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
roots = [36, 43, 45, 41]
arp_pat = [0, 1, 2, 1, 0, 2, 1, 2]
melody = [  # 2小節×2のゆるいメロディ（16分音符単位のオフセット, midi）
    [(0, 76), (4, 74), (6, 72), (8, 74), (12, 79)],
    [(0, 79), (4, 76), (8, 74), (10, 72), (12, 74)],
    [(0, 72), (4, 76), (6, 77), (8, 76), (12, 72)],
    [(0, 69), (4, 72), (8, 74), (12, 72)],
]
bar = 4 * BEAT
nbars = int(dur / bar) + 2
for b in range(nbars):
    t0 = b * bar
    ci = b % 4
    ch = chords[ci]
    sec = (b // 8) % 2  # 8小節ごとにメロディのON/OFF
    add(L, t0, pad([midi(m) for m in ch], bar), 0.05)
    add(R, t0, pad([midi(m + 12) for m in ch], bar), 0.04)
    for k in range(8):
        f = midi(ch[arp_pat[k]] + 12)
        s = pluck(f, BEAT / 2 * 1.5)
        add(L if k % 2 else R, t0 + k * BEAT / 2, s, 0.09)
        add(R if k % 2 else L, t0 + k * BEAT / 2 + 0.11, s, 0.03)  # 簡易ディレイ
    for k in range(4):
        bs = bass(midi(roots[ci]), BEAT * 0.9)
        add(L, t0 + k * BEAT, bs, 0.12)
        add(R, t0 + k * BEAT, bs, 0.12)
        kk = kick()
        add(L, t0 + k * BEAT, kk, 0.35)
        add(R, t0 + k * BEAT, kk, 0.35)
        if k % 2 == 1:
            c = clap()
            add(L, t0 + k * BEAT, c, 0.06)
            add(R, t0 + k * BEAT, c, 0.06)
        for h in (0.5,):
            add(L, t0 + (k + h) * BEAT, hat(), 0.08)
            add(R, t0 + (k + h) * BEAT, hat(), 0.08)
    if sec == 1:
        for off, m in melody[ci]:
            s = pluck(midi(m), BEAT * 1.2)
            add(L, t0 + off * BEAT / 4, s, 0.07)
            add(R, t0 + off * BEAT / 4, s, 0.07)

mix = np.stack([L, R], 1)[: int(SR * dur)]
# フェードイン・アウト
fi, fo = int(0.5 * SR), int(2.0 * SR)
mix[:fi] *= np.linspace(0, 1, fi)[:, None]
mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix /= np.abs(mix).max() + 1e-9
mix *= 0.9
pcm = (mix * 32767).astype(np.int16)
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("bgm", dur, "s ->", out)
