# -*- coding: utf-8 -*-
"""やわらかく上品なBGMを numpy だけで合成する(外部音源なし・権利フリー)。
Fメジャー / 92BPM。エレピ風コード + ベル風アルペジオ + ベース + シェイカー + 軽いキック + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 92
BEAT = 60.0 / BPM
BAR = BEAT * 4

# 4小節ループ: Fmaj7 / Em7 / Dm9 / B♭maj7  (後半は Gm7 / C9sus へ)
PROG = [
    [53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 64], [46, 50, 53, 57],
    [53, 57, 60, 64], [52, 55, 59, 62], [43, 50, 53, 58], [48, 55, 58, 62],
]
ROOTS = [41, 40, 38, 34, 41, 40, 43, 36]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start, sig):
    s = int(start * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def epiano(f, dur, vel=1.0):
    """FM ベースのエレピ風音色"""
    n = int(dur * SR); t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * t) * 1.2 * np.exp(-t / 0.6)
    tone = np.sin(2 * np.pi * f * t + mod) + 0.12 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.15)
    tremolo = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    return (tone * tremolo * np.exp(-t / 1.6) * env_ar(n, 0.005, 0.3) * vel).astype(np.float32)

def bell(f, dur=2.2, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9)
         + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.35)
         + 0.15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.12))
    return (s * env_ar(n, 0.003, 0.2) * vel).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return (s * np.exp(-t / 1.2) * env_ar(n, 0.01, 0.15)).astype(np.float32)

def kick(rng):
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def shaker(rng, vel):
    n = int(0.09 * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(8) / 8, mode='same')       # 低域を削って軽く
    return x * np.exp(-t / 0.025) * env_ar(n, 0.006, 0.02) * vel

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.74), (1877, 0.72), (2251, 0.70), (2687, 0.68))) / 4
    wet = np.convolve(wet, np.ones(6) / 6, mode='same')
    return (1 - mix) * x + mix * wet

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR
    keys, bells, low, perc = (np.zeros(n, dtype=np.float32) for _ in range(4))
    for b in range(int(np.ceil(total / BAR)) + 1):
        t0 = b * BAR; ch = PROG[b % 8]
        # コード: 1拍目と 2.5 拍目に
        for off, v in ((0, 1.0), (2.5 * BEAT, 0.6)):
            for i, m in enumerate(ch):
                add(keys, t0 + off + i * 0.012, epiano(midi(m), BAR, v * (1.0 if i else 0.8)))
        # ベース(4 小節目以降)
        if t0 >= BAR * 2:
            add(low, t0, bass(midi(ROOTS[b % 8]), BEAT * 2.5))
            add(low, t0 + 2.5 * BEAT, bass(midi(ROOTS[b % 8]), BEAT * 1.5) * 0.7)
        # ベル: 8分のアルペジオ(上行→下行)、ところどころ休む
        pat = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[2] + 24, ch[3] + 12, ch[1] + 12, ch[2] + 12]
        for k, m in enumerate(pat):
            if rng.random() < 0.78:
                add(bells, t0 + k * BEAT / 2, bell(midi(m), vel=rng.uniform(0.55, 1.0) * (1.0 if k % 2 == 0 else 0.7)))
        # パーカッション(2 小節目以降)
        if t0 >= BAR:
            for k in range(8):
                add(perc, t0 + k * BEAT / 2, shaker(rng, 0.9 if k % 2 else 0.45))
        if t0 >= BAR * 4:
            add(perc, t0, kick(rng) * 2.2); add(perc, t0 + 2 * BEAT, kick(rng) * 1.6)
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * norm(keys) + 0.30 * reverb(norm(bells), 0.45) + 0.42 * norm(low) + 0.22 * norm(perc)
    mix = reverb(mix, 0.2)[:int(total * SR)]
    mix *= env_ar(len(mix), 1.5, 3.5)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 72
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
