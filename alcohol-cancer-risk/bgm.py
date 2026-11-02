# -*- coding: utf-8 -*-
"""落ち着いた解説系BGMをプログラムで合成する(外部音源不要・権利フリー)。
Aマイナー / 76BPM。柔らかいパッド + 低音ドローン + 控えめな低い打音 + まばらな電子ピアノ風アルペジオ + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 76
BEAT = 60.0 / BPM
BAR = BEAT * 4

# コード進行(MIDIノート)。8小節でループ: Am - F - C - G - Am - F - Dm - E
PROG = [
    [57, 60, 64, 69],  # Am
    [53, 57, 60, 65],  # F
    [48, 52, 55, 60],  # C
    [55, 59, 62, 67],  # G
    [57, 60, 64, 69],  # Am
    [53, 57, 60, 65],  # F
    [50, 53, 57, 62],  # Dm
    [52, 56, 59, 64],  # E
]
ROOTS = [57, 53, 48, 55, 57, 53, 50, 52]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.0015 * np.sin(2 * np.pi * 0.19 * t + rng.uniform(0, 6.28))
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.003, 0.003):
        for h in range(1, 6):
            sig += (1 / h ** 1.9) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + rng.uniform(0, 6.28))
    return sig

def soft_kick(f0=70.0, dur=0.5, rng=None):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 40 + (f0 - 40) * np.exp(-t / 0.07)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(phase) * np.exp(-t / 0.16)).astype(np.float32)

def epiano(f, dur=1.8):
    n = int(dur * SR); t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.2) + 0.08 * np.sin(2 * np.pi * 3 * f * t)
    return (tone * np.exp(-t / 0.45)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.72), (1877, 0.70), (2251, 0.68), (12007, 0.45))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pad = np.zeros(n, dtype=np.float32); drone = np.zeros(n, dtype=np.float32)
    hits = np.zeros(n, dtype=np.float32); arp = np.zeros(n, dtype=np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; chord = PROG[b % 8]
        dur = BAR + 1.2
        sig = sum(pad_note(midi(m), dur, rng) * (0.9 if i < 3 else 0.5) for i, m in enumerate(chord))
        add(pad, t0, sig * env_ar(len(sig), 1.0, 1.2))
        f = midi(ROOTS[b % 8] - 24); tt = np.arange(int(dur * SR)) / SR
        d = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * (1 + 0.1 * np.sin(2 * np.pi * 0.09 * tt))
        add(drone, t0, d.astype(np.float32) * env_ar(len(d), 1.0, 1.2))
        # 控えめな打音: 8 秒以降、1 拍目と 3 拍目
        inten = min(1.0, max(0.0, (t0 - 6) / 16))
        if inten > 0:
            add(hits, t0, soft_kick(rng=rng) * inten)
            add(hits, t0 + 2 * BEAT, soft_kick(f0=62, rng=rng) * 0.6 * inten)
        # 電子ピアノ風アルペジオ(14 秒以降、まばらに)
        if t0 > 14:
            for k in range(8):
                if rng.random() < 0.4:
                    m = chord[rng.integers(0, 4)] + 12
                    add(arp, t0 + k * BEAT / 2, epiano(midi(m)) * rng.uniform(0.4, 0.9))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.6 * norm(pad) + 0.3 * norm(drone) + 0.55 * norm(hits) + 0.2 * reverb(norm(arp), 0.5)
    mix = reverb(mix, 0.2)
    mix *= env_ar(len(mix), 2.0, 4.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 76.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
