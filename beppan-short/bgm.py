# -*- coding: utf-8 -*-
"""サスペンス調の BGM を numpy だけで合成する(外部音源なし・権利フリー)。
A マイナー / 96BPM。低音ドローン + 8 分の脈打つベース + 時計のようなティック + 心拍キック
+ まばらなピアノ風モチーフ。シーンの切り替わりにライザーと低いブームを置く。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 96
BEAT = 60.0 / BPM
BAR = BEAT * 4
ROOTS = [45, 45, 41, 43, 45, 45, 38, 40]            # Am Am F G | Am Am Dm E
MOTIF = [(0, 76), (1.5, 72), (2, 71), (3, 69)], [(0, 76), (1.5, 77), (2, 76), (3.5, 72)], \
        [(0, 72), (1.5, 69), (2, 65), (3, 69)], [(0, 71), (1.5, 74), (2, 71), (3, 67)]

def hz(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, t, sig):
    s = int(t * SR)
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]
def box(x, k): return np.convolve(x, np.ones(k, dtype=np.float32) / k, mode='same')
def tt(dur): return np.arange(int(dur * SR), dtype=np.float32) / SR

def bass(f, dur=0.3):
    t = tt(dur)
    sig = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 6))
    return (sig * np.exp(-t / 0.11) * np.minimum(1, t / 0.004)).astype(np.float32)
def tick(rng, dur=0.05):
    t = tt(dur); n = rng.standard_normal(len(t)).astype(np.float32)
    return (n - box(n, 12)) * np.exp(-t / 0.008)
def kick(dur=0.45):
    t = tt(dur); f = 42 + 60 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)).astype(np.float32)
def piano(f, dur=2.4):
    t = tt(dur)
    sig = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (1.6 + 0.9 * h)) for h, a in ((1, 1), (2, .45), (3, .2), (4, .08)))
    return (sig * np.minimum(1, t / 0.003)).astype(np.float32)
def boom(dur=2.6):
    t = tt(dur); f = 34 + 40 * np.exp(-t / 0.25)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)).astype(np.float32)
def riser(rng, dur=1.4):
    t = tt(dur); n = rng.standard_normal(len(t)).astype(np.float32)
    n = box(n, 40) * 3 + 0.3 * (n - box(n, 8))
    return n * (t / dur) ** 3
def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y
def reverb(x, mix):
    wet = sum(comb(x, d, g) for d, g in ((1617, .74), (1949, .72), (2311, .70), (10007, .5))) / 4
    return (1 - mix) * x + mix * box(wet, 6)
def norm(x): return x / (np.max(np.abs(x)) + 1e-9)

def generate(total, scene_starts=(), seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR); z = lambda: np.zeros(n, dtype=np.float32)
    drone, bs, tk, kk, pn, fx = z(), z(), z(), z(), z(), z()
    t = np.arange(n, dtype=np.float32) / SR
    for f, a in ((55, 1), (55.4, .6), (110, .35), (164.8, .12)):
        drone += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * (1 + 0.25 * np.sin(2 * np.pi * 0.07 * t + f))
    t_pulse = scene_starts[1] if len(scene_starts) > 1 else 6.0     # 2 シーン目からリズムが入る
    last = scene_starts[-1] if len(scene_starts) else total
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; root = ROOTS[b % 8]
        if t0 >= t_pulse - BAR:
            lvl = min(1.0, max(0.25, (t0 - t_pulse + BAR) / 12))
            for k in range(8):
                add(bs, t0 + k * BEAT / 2, bass(hz(root - 12 if k % 4 else root - 12)) * (1.0 if k % 2 == 0 else 0.6) * lvl)
            for k in range(16):
                add(tk, t0 + k * BEAT / 4, tick(rng) * (1.0 if k % 4 == 2 else 0.35) * lvl)
            add(kk, t0, kick()); add(kk, t0 + 0.75 * BEAT, kick() * 0.55); add(kk, t0 + 2 * BEAT, kick() * 0.8)
        if b % 2 == 0 or t0 >= last:
            for beat, note in MOTIF[(b // 2) % 4]:
                add(pn, t0 + beat * BEAT, piano(hz(note)) * rng.uniform(0.7, 1.0))
    for s in scene_starts[1:]:
        r = riser(rng); add(fx, s - len(r) / SR, r * 0.5); add(fx, s, boom())
    add(fx, 0.0, boom() * 0.8)
    mix = (0.42 * norm(drone) + 0.42 * norm(bs) + 0.10 * norm(tk) + 0.50 * norm(kk)
           + 0.40 * reverb(norm(pn), 0.45) + 0.55 * norm(fx))
    mix = reverb(mix, 0.12)
    env = np.ones(n, dtype=np.float32)
    a, r = int(1.0 * SR), int(2.5 * SR)
    env[:a] = np.linspace(0, 1, a); env[-r:] = np.linspace(1, 0, r) ** 1.5
    return (norm(mix * env) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total, [0, 7, 20, 34, 46, 55])
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out)
