# -*- coding: utf-8 -*-
"""明るく好奇心を感じる科学番組風BGMをプログラムで合成する(外部音源不要・権利フリー)。
Cメジャー / 104BPM。マリンバ風アルペジオ + ベル + 柔らかいパッド + ベース + 軽いキック/シェイカー + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 104
BEAT = 60.0 / BPM
BAR = BEAT * 4
# I - V/vi... 明るい 4 小節進行 x2(後半はサブドミナント寄り)
PROG = [
    [60, 64, 67, 71],  # Cmaj7
    [57, 60, 64, 67],  # Am7
    [53, 57, 60, 64],  # Fmaj7
    [55, 59, 62, 65],  # G7
    [60, 64, 67, 71],  # Cmaj7
    [52, 55, 59, 62],  # Em7
    [53, 57, 60, 64],  # Fmaj7
    [55, 59, 62, 67],  # G
]
ROOTS = [48, 45, 41, 43, 48, 40, 41, 43]
ARP = [0, 1, 2, 3, 2, 1, 2, 3]  # 8 分音符アルペジオの並び

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def marimba(f, dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.18) + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.03)
    s[:48] *= np.linspace(0, 1, 48)
    return s.astype(np.float32)

def bell(f, dur=2.0):
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.3)
         + 0.25 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t / 0.12)) * np.exp(-t / 0.7)
    s[:48] *= np.linspace(0, 1, 48)
    return s.astype(np.float32)

def pad_chord(chord, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for m in chord:
        f = midi(m)
        for det in (-0.003, 0.003):
            for h in range(1, 5):
                sig += (1 / h ** 2) * np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6.28))
    return sig * env_ar(n, 0.6, 0.8)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.5)
    return (s * env_ar(n, 0.005, 0.05)).astype(np.float32)

def kick(dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def shaker(rng, dur=0.08):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(8) / 8, mode='same')  # 高域だけ残す
    return x * np.exp(-t / 0.02).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (9001, 0.4))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pad, mar, bel, bas, drm = (np.zeros(n, dtype=np.float32) for _ in range(5))
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; chord = PROG[b % 8]; root = ROOTS[b % 8]
        add(pad, t0, pad_chord(chord, BAR + 0.8, rng))
        # マリンバのアルペジオ(1 小節目から)
        for k in range(8):
            m = chord[ARP[k]] + 12
            add(mar, t0 + k * BEAT / 2, marimba(midi(m)) * (1.0 if k % 2 == 0 else 0.7))
        # ベース(2 小節目以降): 1 拍目と 3 拍目裏
        if b >= 1:
            add(bas, t0, bass(midi(root), BEAT * 1.5))
            add(bas, t0 + 2.5 * BEAT, bass(midi(root + 7 if b % 2 else root), BEAT * 1.4) * 0.8)
        # ドラム(2 小節目以降、軽め)
        if b >= 2:
            for k in (0, 2): add(drm, t0 + k * BEAT, kick())
            for k in range(8): add(drm, t0 + k * BEAT / 2, shaker(rng) * (0.25 if k % 2 == 0 else 0.45))
        # ベル: 2 小節に 1 度、きらっと
        if b % 2 == 1:
            add(bel, t0 + 3 * BEAT, bell(midi(chord[3] + 24)) * 0.8)
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.30 * norm(pad) + 0.50 * reverb(norm(mar), 0.3) + 0.22 * reverb(norm(bel), 0.5)
           + 0.45 * norm(bas) + 0.40 * norm(drm))
    mix = reverb(mix, 0.12)
    mix *= env_ar(len(mix), 1.0, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 68.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
