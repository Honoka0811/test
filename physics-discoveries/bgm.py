# -*- coding: utf-8 -*-
"""ワクワク感のある科学番組風BGMを numpy だけで合成する(外部音源なし・権利フリー)。
Cメジャー / 100BPM。やわらかいパッド + ベル風アルペジオ + ベース + 軽いキック/ハイハット + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 100
BEAT = 60.0 / BPM
BAR = BEAT * 4
# C - G/B - Am - F - C - Em - F - G (8小節ループ)
PROG = [[60, 64, 67, 72], [59, 62, 67, 71], [57, 60, 64, 69], [53, 57, 60, 65],
        [60, 64, 67, 72], [59, 64, 67, 71], [53, 57, 60, 65], [55, 59, 62, 67]]
ROOTS = [48, 47, 45, 41, 48, 40, 41, 43]
ARP = [0, 1, 2, 3, 2, 1, 3, 2]  # 8分音符ごとのコード構成音インデックス

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start, sig):
    s = int(start * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.003, 0.0, 0.003):
        for h in range(1, 5):
            sig += (1 / h ** 2) * np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6.28))
    return sig

def bell(f, dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    # FM ベル: キラッとした音色
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 1.6 * np.exp(-t / 0.25)
    return (np.sin(2 * np.pi * f * t + mod) * np.exp(-t / 0.45)).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return (s * env_ar(n, 0.01, 0.15) * np.exp(-t / 0.9)).astype(np.float32)

def kick(dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 45 + 90 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def hat(rng, dur=0.06):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(8) / 8, mode='same')  # 簡易ハイパス
    return x * np.exp(-t / 0.015)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (2719, 0.64))) / 4
    return (1 - mix) * x + mix * wet

def delay_fx(x, sec, fb=0.35, mix=0.3):
    d = int(sec * SR); y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += fb * y[s - d:e - d]
    return (1 - mix) * x + mix * y

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pad, bel, bs, drum = (np.zeros(n, dtype=np.float32) for _ in range(4))
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; ch = PROG[b % 8]
        dur = BAR + 0.8
        sig = sum(pad_note(midi(m), dur, rng) for m in ch[:3])
        add(pad, t0, sig * env_ar(len(sig), 0.4, 0.8))
        for k in range(8):  # 8分のベルアルペジオ(1オクターブ上)
            vel = 1.0 if k % 2 == 0 else 0.7
            add(bel, t0 + k * BEAT / 2, bell(midi(ch[ARP[k]] + 12)) * vel)
        if t0 >= BAR * 2:  # 3小節目からベースとビート
            r = midi(ROOTS[b % 8])
            for k, l in ((0, 1.4), (1.5, 0.45), (2, 1.4), (3.5, 0.45)):
                add(bs, t0 + k * BEAT, bass(r, l * BEAT))
            for k in range(4):
                add(drum, t0 + k * BEAT, kick() * (1.0 if k % 2 == 0 else 0.6))
            for k in range(8):
                add(drum, t0 + k * BEAT / 2, hat(rng) * (0.15 if k % 2 else 0.08))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.45 * norm(pad) + 0.32 * delay_fx(norm(bel), BEAT * 0.75) + 0.45 * norm(bs) + 0.45 * norm(drum)
    mix = reverb(mix, 0.2)
    mix *= env_ar(len(mix), 1.0, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 74
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
