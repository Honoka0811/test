# -*- coding: utf-8 -*-
"""やさしく明るいお仕事紹介風BGMを numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 96BPM。王道進行(F→G→Em→Am)のエレピ風コード + ベース + 軽いキック/シェイカー + 鉄琴風メロディ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 96
BEAT = 60.0 / BPM
BAR = BEAT * 4

# 4小節ループ: F G Em Am(MIDI)
PROG = [[53, 57, 60, 64], [55, 59, 62, 65], [52, 55, 59, 62], [57, 60, 64, 67]]
ROOTS = [41, 43, 40, 45]
# 鉄琴メロディ(小節内の8分音符位置, MIDI)。0 は休符
MELODY = [
    [72, 0, 69, 0, 72, 74, 0, 76],
    [74, 0, 71, 0, 67, 0, 0, 0],
    [71, 0, 67, 0, 71, 72, 0, 74],
    [72, 0, 0, 69, 0, 0, 0, 0],
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def ep(f, dur):
    """エレピ風: 基音 + 弱い倍音 + ベル成分、指数減衰"""
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.4) \
        + 0.12 * np.sin(2 * np.pi * 7 * f * t) * np.exp(-t / 0.05)
    env = np.exp(-t / 1.1) * np.minimum(1, t / 0.004)
    rel = np.minimum(1, (dur - t) / 0.08)
    return (s * env * rel).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return (s * np.exp(-t / 0.6) * np.minimum(1, t / 0.005) * np.minimum(1, (dur - t) / 0.05)).astype(np.float32)

def bell(f, dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.15)
    return (s * np.exp(-t / 0.45) * np.minimum(1, t / 0.002)).astype(np.float32)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def shaker(rng):
    n = int(0.08 * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(8) / 8, mode='same')  # 高域だけ残す
    return (x * np.exp(-t / 0.02)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.55), (2903, 0.5))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    keys, low, drums, mel = (np.zeros(n, dtype=np.float32) for _ in range(4))
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; i = b % 4
        # コード: 1拍目と「3拍目の裏」に刻む
        for off, v in ((0, 1.0), (2.5 * BEAT, 0.6)):
            add(keys, t0 + off, sum(ep(midi(m), 1.6) for m in PROG[i]) * v)
        # ベース: 1拍目・3拍目
        add(low, t0, bass(midi(ROOTS[i]), 1.4 * BEAT))
        add(low, t0 + 2 * BEAT, bass(midi(ROOTS[i] + (7 if i % 2 else 12)), 1.4 * BEAT) * 0.8)
        # リズム(4小節目以降)
        if b >= 2:
            for k in range(4):
                add(drums, t0 + k * BEAT, kick() * (1.0 if k % 2 == 0 else 0.55))
            for k in range(8):
                add(drums, t0 + k * BEAT / 2, shaker(rng) * (0.35 if k % 2 else 0.18))
        # メロディ(8小節目以降、ナレーションの邪魔をしない控えめな音量)
        if b >= 4:
            for k, m in enumerate(MELODY[i]):
                if m: add(mel, t0 + k * BEAT / 2, bell(midi(m)))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * norm(keys) + 0.5 * norm(low) + 0.35 * norm(drums) + 0.22 * norm(mel)
    mix = reverb(mix, 0.22)
    env = np.ones(n, dtype=np.float32)
    fi, fo = int(1.0 * SR), int(3.5 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    mix *= env
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 64.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
