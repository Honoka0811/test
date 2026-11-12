# -*- coding: utf-8 -*-
"""軽快なポップ系BGMを numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 112BPM。マリンバ風メロディ + オフビートのコード + ベース + キック/シェイカー + 水中っぽい泡の効果音。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 112
BEAT = 60.0 / BPM
BAR = BEAT * 4

PROG = [  # C - Am - F - G (2周目は C - Em - F - G)
    [60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62],
    [60, 64, 67], [52, 55, 59], [53, 57, 60], [55, 59, 62],
]
ROOTS = [48, 45, 41, 43, 48, 40, 41, 43]
# メロディ(1小節 = 8分音符 8つ, None = 休符)。コードトーン中心
MEL = [
    [72, None, 76, 79, None, 76, 74, None],
    [72, None, 69, None, 72, 76, None, None],
    [77, None, 76, 74, None, 72, 69, None],
    [71, 72, 74, None, 79, None, 74, None],
    [76, None, 79, 84, None, 79, 76, None],
    [71, None, 74, None, 76, 79, None, None],
    [77, 76, 74, None, 72, None, 69, 72],
    [74, None, 71, None, 67, None, None, None],
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def tvec(dur): return np.arange(int(dur * SR)) / SR

def marimba(f, dur=0.6):
    t = tvec(dur)
    return ((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.03))
            * np.exp(-t / 0.18) * (1 - np.exp(-t / 0.002))).astype(np.float32)

def keys(f, dur=0.25):
    t = tvec(dur)
    s = sum((1 / h) * np.sin(2 * np.pi * f * h * t) for h in (1, 2, 3))
    return (s * np.exp(-t / 0.09) * (1 - np.exp(-t / 0.003))).astype(np.float32)

def bass(f, dur):
    t = tvec(dur)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return (s * np.exp(-t / 0.35) * (1 - np.exp(-t / 0.005))).astype(np.float32)

def kick():
    t = tvec(0.35)
    f = 50 + 90 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def shaker(rng, dur=0.07):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(8) / 8, mode='same')  # 高域寄りに
    return (x * np.exp(-t / 0.018)).astype(np.float32)

def bloop(f0, dur=0.18):
    t = tvec(dur)
    f = f0 * (1 + 2.5 * t / dur)  # 上昇する泡の音
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / dur) ** 2).astype(np.float32)

def echo(x, delay_s=BEAT * 0.75, g=0.3, n=3):
    y = x.copy(); d = int(delay_s * SR)
    for k in range(1, n + 1):
        y[d * k:] += (g ** k) * x[:len(x) - d * k]
    return y

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    mel = np.zeros(n, np.float32); chd = np.zeros(n, np.float32); bas = np.zeros(n, np.float32)
    drm = np.zeros(n, np.float32); fx = np.zeros(n, np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; i = b % 8
        intro = b < 2
        for k in range(4):  # 4つ打ち + オフビートのコード
            if not intro or k % 2 == 0:
                add(drm, t0 + k * BEAT, kick() * (0.6 if intro else 1.0))
            for m in PROG[i]:
                add(chd, t0 + (k + .5) * BEAT, keys(midi(m)) * 0.5)
        if not intro:
            for k in range(8):
                add(drm, t0 + k * BEAT / 2, shaker(rng) * (0.35 if k % 2 else 0.2))
        # ベース(ルート → 5度)
        add(bas, t0, bass(midi(ROOTS[i]), BEAT * 1.9))
        add(bas, t0 + 2 * BEAT, bass(midi(ROOTS[i] + 7), BEAT * 0.9))
        add(bas, t0 + 3 * BEAT, bass(midi(ROOTS[i]), BEAT * 0.9))
        if not intro:
            for k, m in enumerate(MEL[i]):
                if m is not None:
                    add(mel, t0 + k * BEAT / 2, marimba(midi(m)) * rng.uniform(.8, 1.0))
        if b % 4 == 3:  # 4小節ごとに泡の効果音
            for q in range(3):
                add(fx, t0 + 3 * BEAT + q * 0.09, bloop(500 + 180 * q))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * echo(norm(mel)) + 0.32 * norm(chd) + 0.55 * norm(bas) + 0.5 * norm(drm) + 0.18 * norm(fx)
    env = np.ones(n, np.float32)
    fi, fo = int(0.5 * SR), int(3.0 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    mix = mix * env
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 53
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
