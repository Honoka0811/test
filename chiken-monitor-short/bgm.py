# -*- coding: utf-8 -*-
"""明るく軽いポップ調のBGMを numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 108BPM。マリンバ風アルペジオ + ベース + やわらかいキック/シェイカー/クラップ + パッド。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 108
BEAT = 60.0 / BPM
BAR = BEAT * 4

# F△7 → G → Em7 → Am7 / F△7 → G → C → C (8小節ループ)
PROG = [
    (41, [65, 69, 72, 76]),
    (43, [67, 71, 74, 79]),
    (40, [64, 67, 71, 74]),
    (45, [64, 69, 72, 76]),
    (41, [65, 69, 72, 76]),
    (43, [67, 71, 74, 79]),
    (36, [64, 67, 72, 76]),
    (36, [67, 72, 76, 79]),
]
ARP = [0, 2, 1, 3, 2, 1, 3, 2]  # 8分音符のアルペジオ順


def hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, start, sig, gl=1.0, gr=1.0):
    s = int(start * SR)
    e = min(s + len(sig), len(buf))
    if e > s >= 0:
        buf[s:e, 0] += sig[:e - s] * gl
        buf[s:e, 1] += sig[:e - s] * gr


def marimba(f, dur=0.9):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.22)
    x += 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.05)
    x += 0.12 * np.sin(2 * np.pi * 10 * f * t) * np.exp(-t / 0.015)
    x[:96] *= np.linspace(0, 1, 96)
    return x.astype(np.float32)


def bass(f, dur):
    t = np.arange(int(dur * SR)) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.45)
    n = len(x); a = 240; r = min(1200, n // 2)
    x[:a] *= np.linspace(0, 1, a); x[-r:] *= np.linspace(1, 0, r)
    return x.astype(np.float32)


def kick():
    t = np.arange(int(0.3 * SR)) / SR
    f = 48 + 90 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)).astype(np.float32)


def noise_hit(rng, decay, smooth):
    n = int(decay * 6 * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t / decay)
    if smooth > 1:
        x = x - np.convolve(x, np.ones(smooth) / smooth, mode='same')  # 低域を落として軽く
    return x.astype(np.float32)


def pad(notes, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for m in notes:
        f = hz(m - 12)
        for det in (-0.003, 0.003):
            x += np.sin(2 * np.pi * f * (1 + det) * t + rng.uniform(0, 6.28))
            x += 0.3 * np.sin(2 * np.pi * 2 * f * (1 + det) * t + rng.uniform(0, 6.28))
    a = int(0.25 * SR); r = int(0.4 * SR)
    x[:a] *= np.linspace(0, 1, a); x[-r:] *= np.linspace(1, 0, r)
    return (x / len(notes)).astype(np.float32)


def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y


def reverb(x, mix=0.22):
    out = np.empty_like(x)
    for ch, off in ((0, 0), (1, 37)):
        wet = sum(comb(x[:, ch], d + off, g) for d, g in ((1553, 0.62), (1877, 0.60), (2251, 0.58))) / 3
        out[:, ch] = (1 - mix) * x[:, ch] + mix * wet
    return out


def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    mel = np.zeros((n, 2), dtype=np.float32)
    low = np.zeros((n, 2), dtype=np.float32)
    drums = np.zeros((n, 2), dtype=np.float32)
    k = kick()
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR
        root, chord = PROG[b % len(PROG)]
        intro = b < 2                      # 冒頭2小節はドラムなしで静かに入る
        add(mel, t0, pad(chord, BAR + 0.3, rng), 0.10, 0.10)
        for i in range(8):                 # 8分音符のアルペジオ(左右に少し振る)
            note = chord[ARP[i]] + (12 if (b % 2 == 1 and i in (3, 7)) else 0)
            vel = 0.30 if i % 2 == 0 else 0.22
            pan = 0.5 + 0.3 * np.sin(i * 1.7 + b)
            add(mel, t0 + i * BEAT / 2, marimba(hz(note)), vel * (1 - pan) * 2, vel * pan * 2)
        for beat, dur in ((0, 1.4), (1.5, 0.5), (2.5, 1.4)):
            add(low, t0 + beat * BEAT, bass(hz(root), dur * BEAT), 0.36, 0.36)
        if not intro:
            for beat in (0, 2):
                add(drums, t0 + beat * BEAT, k, 0.42, 0.42)
            for beat in (1, 3):
                add(drums, t0 + beat * BEAT, noise_hit(rng, 0.035, 24), 0.10, 0.12)
            for i in range(8):
                g = 0.045 if i % 2 else 0.022
                add(drums, t0 + i * BEAT / 2, noise_hit(rng, 0.012, 6), g * 1.1, g * 0.9)
    mix = reverb(mel) + low + drums
    fo = int(2.0 * SR); fi = int(0.3 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return (mix / np.max(np.abs(mix)) * 0.9).astype(np.float32)


if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x.reshape(-1) * 32767).astype(np.int16).tobytes())
    print('wrote', out)
