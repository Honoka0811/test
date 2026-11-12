# -*- coding: utf-8 -*-
"""明るく軽いBGMを numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 96BPM。マリンバ風アルペジオ + 柔らかいパッド + ベース + 軽いキックとシェイカー。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 96
BEAT = 60.0 / BPM
BAR = BEAT * 4
# 8小節ループ: C  G/B  Am  F  C  G  F  G
PROG = [
    ([60, 64, 67, 72], 36), ([59, 62, 67, 74], 35), ([57, 60, 64, 72], 33), ([57, 60, 65, 72], 29),
    ([60, 64, 67, 76], 36), ([59, 62, 67, 74], 31), ([57, 60, 65, 69], 29), ([59, 62, 67, 71], 31),
]
ARP = [0, 2, 1, 3, 2, 1, 3, 2]  # 8分音符のアルペジオ型

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def marimba(f, dur=0.9):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.22) + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.05)
    x[:96] *= np.linspace(0, 1, 96)
    return x.astype(np.float32)

def pad(f, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum((1 / h ** 2) * np.sin(2 * np.pi * f * h * (1 + d) * t) for h in (1, 2, 3) for d in (-0.003, 0.003))
    return x.astype(np.float32)

def bass(f, dur):
    t = np.arange(int(dur * SR)) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.5)
    x[:240] *= np.linspace(0, 1, 240)
    return x.astype(np.float32)

def kick():
    t = np.arange(int(0.25 * SR)) / SR
    f = 50 + 70 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.09)).astype(np.float32)

def shaker(rng, dur=0.07):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(24) / 24, mode='same')  # 低域を落として「シャッ」とした音に
    return x * np.exp(-t / 0.02)

def echo(x, delay_s, g, taps=4):
    y = x.copy(); d = int(delay_s * SR)
    for k in range(1, taps + 1):
        y[k * d:] += (g ** k) * x[:len(x) - k * d]
    return y

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    L = {k: np.zeros(n, dtype=np.float32) for k in ('arp', 'pad', 'bass', 'kick', 'shk')}
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; chord, root = PROG[b % 8]
        sig = sum(pad(midi(m - 12), BAR + 0.8) for m in chord[:3])
        add(L['pad'], t0, sig * env_ar(len(sig), 0.6, 0.8))
        add(L['bass'], t0, bass(midi(root), BEAT * 2))
        add(L['bass'], t0 + 2.5 * BEAT, bass(midi(root), BEAT * 1.5) * 0.7)
        full = b >= 2  # 最初の2小節はパッドとアルペジオだけ
        for k in range(8):
            vel = (1.0 if k % 2 == 0 else 0.7) * rng.uniform(0.85, 1.0)
            add(L['arp'], t0 + k * BEAT / 2, marimba(midi(chord[ARP[k]] + 12)) * vel)
            if full and k % 2 == 1:
                add(L['shk'], t0 + k * BEAT / 2, shaker(rng) * 0.8)
        if full:
            add(L['kick'], t0, kick()); add(L['kick'], t0 + 2 * BEAT, kick() * 0.8)
    norm = lambda x: x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.55 * echo(norm(L['arp']), BEAT * 0.75, 0.35) + 0.30 * norm(L['pad']) + 0.45 * norm(L['bass'])
           + 0.40 * norm(L['kick']) + 0.10 * norm(L['shk']))
    mix *= env_ar(n, 1.0, 3.0)
    return (mix / np.max(np.abs(mix)) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
