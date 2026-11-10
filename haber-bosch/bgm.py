# -*- coding: utf-8 -*-
"""サイエンス解説風の軽快なBGMをプログラムで合成する(外部音源不要・権利フリー)。
Cメジャー / 100BPM。マリンバ風アルペジオ + やわらかいパッド + ベース + キック/シェイカー。
「影の面」のシーン(56〜64秒)だけ Aマイナー寄りの暗い進行・薄いリズムに切り替える。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 100
BEAT = 60.0 / BPM
BAR = BEAT * 4
BRIGHT = [[60, 64, 67, 72], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]   # C G Am F
DARK = [[57, 60, 64, 69], [53, 57, 60, 65], [50, 53, 57, 62], [52, 56, 59, 64]]     # Am F Dm E
DARK_RANGE = (55.0, 63.5)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if 0 <= s < e: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def marimba(f, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.28) + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.05)
    return (s * np.minimum(1, t / 0.003)).astype(np.float32)

def pad(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n, dtype=np.float32)
    for det in (-0.003, 0.0, 0.003):
        for h in (1, 2, 3):
            s += (1 / h ** 2) * np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6.28))
    return s

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.5) * np.minimum(1, t / 0.01)).astype(np.float32)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def shaker(rng):
    n = int(0.08 * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.concatenate([[0], x[:-1]])  # 簡易ハイパス
    return x * np.exp(-t / 0.02).astype(np.float32)

def reverb(x, mix=0.25):
    def comb(x, d, g):
        y = x.copy()
        for s in range(d, len(y), d):
            e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
        return y
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.55), (3307, 0.5))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    tr = {k: np.zeros(n, dtype=np.float32) for k in ('pad', 'arp', 'bass', 'kick', 'shk')}
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]  # 8分音符のアルペジオ順
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR
        dark = DARK_RANGE[0] <= t0 < DARK_RANGE[1]
        chord = (DARK if dark else BRIGHT)[b % 4]
        add(tr['pad'], t0, sum(pad(midi(m), BAR + 0.6, rng) for m in chord[:3]) * env_ar(int((BAR + .6) * SR), .4, .6))
        for k in range(2):
            add(tr['bass'], t0 + k * 2 * BEAT, bass(midi(chord[0] - 24), 2 * BEAT))
        intro = t0 < 5.5
        for k, idx in enumerate(pattern):
            if dark and k % 2: continue
            if intro and k % 2: continue
            m = chord[idx] + 12 + (12 if (k == 7 and not dark) else 0)
            add(tr['arp'], t0 + k * BEAT / 2, marimba(midi(m)) * (1.0 if k % 2 == 0 else 0.7))
        if not intro:
            for k in range(4):
                if not dark or k in (0, 2):
                    add(tr['kick'], t0 + k * BEAT, kick() * (1.0 if k % 2 == 0 else 0.6))
            if not dark:
                for k in range(8):
                    add(tr['shk'], t0 + k * BEAT / 2, shaker(rng) * (0.5 if k % 2 == 0 else 1.0))
    norm = lambda x: x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.35 * norm(tr['pad']) + 0.55 * reverb(norm(tr['arp']), .3) + 0.45 * norm(tr['bass'])
           + 0.55 * norm(tr['kick']) + 0.12 * norm(tr['shk']))
    mix = reverb(mix, 0.12) * env_ar(n, 1.0, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 70
    out = sys.argv[2] if len(sys.argv) > 2 else 'output/bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
