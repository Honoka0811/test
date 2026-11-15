# -*- coding: utf-8 -*-
"""明るいポップ調BGMを numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 118BPM。王道進行(F-G-Em-Am)。キック・クラップ・ハイハット・ベース・裏拍のコードスタブ・グロッケン風メロディ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 118
BEAT = 60.0 / BPM
BAR = BEAT * 4

PROG = [  # (ルート, コード構成音) MIDI
    (41, [65, 69, 72]),  # F
    (43, [67, 71, 74]),  # G
    (40, [64, 67, 71]),  # Em
    (45, [69, 72, 76]),  # Am
]
# グロッケンのモチーフ(8分音符 × 8、コード構成音のインデックス。None = 休符)
MOTIF = [[2, None, 1, 2, None, 0, 1, None], [0, 1, 2, None, 2, 1, None, 0]]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tvec(dur): return np.arange(int(dur * SR)) / SR

def add(buf, start_s, sig, g=1.0):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += g * sig[:e - s]

def kick(rng):
    t = tvec(0.32)
    f = 48 + 110 * np.exp(-t / 0.035)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    return (np.tanh(1.6 * s) + 0.15 * rng.standard_normal(len(t)) * np.exp(-t / 0.004)).astype(np.float32)

def clap(rng):
    t = tvec(0.25); n = rng.standard_normal(len(t))
    n = n - np.convolve(n, np.ones(6) / 6, mode='same')  # 低域を削る
    env = np.exp(-t / 0.07) * (1 + 0.6 * np.exp(-((t - 0.012) / 0.003) ** 2) + 0.5 * np.exp(-((t - 0.024) / 0.003) ** 2))
    return (n * env * 0.6).astype(np.float32)

def hat(rng, dur=0.06):
    t = tvec(dur); n = rng.standard_normal(len(t))
    n = np.diff(np.diff(n, prepend=0), prepend=0)
    return (n * np.exp(-t / 0.018) * 0.15).astype(np.float32)

def bass(f, dur):
    t = tvec(dur)
    s = sum((1 / h) * np.sin(2 * np.pi * f * h * t) for h in range(1, 7))
    env = np.minimum(1, t / 0.005) * np.exp(-t / 0.18)
    return (s * env).astype(np.float32)

def stab(notes, dur=0.16):
    t = tvec(dur)
    s = sum(np.sign(np.sin(2 * np.pi * midi(m) * t)) * 0.5 + np.sin(2 * np.pi * midi(m) * t) for m in notes)
    s = np.convolve(s, np.ones(10) / 10, mode='same')  # 角を丸める
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.06)
    return (s * env).astype(np.float32)

def pad(notes, dur):
    t = tvec(dur); s = np.zeros(len(t))
    for m in notes:
        for det in (-0.003, 0.003):
            s += np.sin(2 * np.pi * midi(m - 12) * (1 + det) * t) + 0.3 * np.sin(2 * np.pi * midi(m) * (1 + det) * t)
    env = np.minimum(1, t / 0.3) * np.minimum(1, (dur - t) / 0.3)
    return (s * env).astype(np.float32)

def glock(f, dur=0.9):
    t = tvec(dur)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.08) + 0.15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.04)
    return (s * np.exp(-t / 0.35)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.55), (2617, 0.5))) / 4
    return (1 - mix) * x + mix * wet

def env_ar(n, a, r):
    e = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    e[:na] = np.linspace(0, 1, na); e[n - nr:] = np.linspace(1, 0, nr)
    return e

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    drums, bs, st, pd, gl = (np.zeros(n, dtype=np.float32) for _ in range(5))
    K, CL = kick(rng), clap(rng)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; root, chord = PROG[b % 4]
        intro = b < 2
        add(pd, t0, pad(chord, BAR + 0.05))
        for k in range(4):  # 拍
            tb = t0 + k * BEAT
            if not intro:
                add(drums, tb, K, 1.0)
                if k in (1, 3): add(drums, tb, CL, 0.55)
            add(drums, tb + BEAT / 2, hat(rng), 1.0 if not intro else 0.6)
            add(drums, tb, hat(rng, 0.03), 0.35)
            add(st, tb + BEAT / 2, stab(chord))  # 裏拍のスタブ
        for k in range(8):  # ベース 8分(オクターブ跳躍)
            if intro and k % 2: continue
            f = midi(root + (12 if k % 2 else 0))
            add(bs, t0 + k * BEAT / 2, bass(f, BEAT / 2 + 0.02), 1.0 if k % 2 == 0 else 0.7)
        if b >= 2:  # メロディ
            mot = MOTIF[(b // 4) % 2]
            for k, idx in enumerate(mot):
                if idx is None: continue
                add(gl, t0 + k * BEAT / 2, glock(midi(chord[idx] + 12)), rng.uniform(0.75, 1.0))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * norm(drums) + 0.55 * norm(bs) + 0.30 * norm(st) + 0.25 * norm(pd) + 0.34 * reverb(norm(gl), 0.35)
    mix = reverb(mix, 0.08)
    mix *= env_ar(len(mix), 0.3, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
