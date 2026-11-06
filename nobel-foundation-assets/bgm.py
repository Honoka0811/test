# -*- coding: utf-8 -*-
"""明るめの解説系BGMをプログラムで合成する(外部音源不要・権利フリーの自作曲)。
Cメジャー / 100BPM。進行 F-G-Em-Am / F-G-C-C。
エレピ風コード + ベース + キック/クラップ/ハイハット + ベルのメロディ + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 100
BEAT = 60.0 / BPM
BAR = BEAT * 4

PROG = [
    [53, 57, 60, 64],  # Fmaj7
    [55, 59, 62, 65],  # G7
    [52, 55, 59, 62],  # Em7
    [57, 60, 64, 67],  # Am7
    [53, 57, 60, 64],  # Fmaj7
    [55, 59, 62, 65],  # G7
    [48, 52, 55, 59],  # Cmaj7
    [48, 52, 55, 60],  # C
]
ROOTS = [41, 43, 40, 45, 41, 43, 36, 36]
# ベルのメロディ(小節内の 8 分音符位置, MIDI)。2 小節ずつのモチーフ
MELODY = [
    [(0, 72), (2, 74), (3, 76), (6, 77)],
    [(0, 76), (2, 74), (4, 71), (6, 74)],
    [(0, 71), (2, 72), (3, 74), (6, 76)],
    [(0, 72), (3, 69), (4, 72), (6, 76)],
    [(0, 77), (2, 76), (3, 74), (6, 72)],
    [(0, 74), (2, 76), (4, 77), (6, 79)],
    [(0, 76), (2, 74), (4, 72), (6, 71)],
    [(0, 72)],
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def epiano(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.4))
    s += 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.3)
    return (s * np.exp(-t / 1.2) * env_ar(n, 0.005, 0.08)).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return (s * np.exp(-t / 0.6) * env_ar(n, 0.005, 0.05)).astype(np.float32)

def bell(f, dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t / 0.15) + 0.2 * np.sin(2 * np.pi * f * 4.2 * t) * np.exp(-t / 0.08)
    return (s * np.exp(-t / 0.45) * env_ar(n, 0.002, 0.05)).astype(np.float32)

def kick(rng):
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def noise_hit(rng, dur, decay, smooth):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    lo = np.convolve(x, np.ones(smooth) / smooth, mode='same')
    return ((x - lo) * np.exp(-t / decay)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (2719, 0.62))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    keys = np.zeros(n, np.float32); bs = np.zeros(n, np.float32); drm = np.zeros(n, np.float32)
    hat = np.zeros(n, np.float32); mel = np.zeros(n, np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; chord = PROG[b % 8]; root = midi(ROOTS[b % 8])
        last = t0 > total - BAR * 1.5  # 最後の小節は伸ばして終わる
        # エレピ: 1拍目と 2.5 拍目(シンコペーション)
        for off, vel in ((0, 1.0), (1.5 * BEAT, 0.6), (2.5 * BEAT, 0.75)):
            if last and off > 0: continue
            for m in chord:
                add(keys, t0 + off, epiano(midi(m), 1.6 if not last else 3.5) * vel)
        # ベース: 8 分で刻む(ルート / オクターブ)
        for k in range(8 if not last else 1):
            f = root * (2 if k in (3, 7) else 1)
            add(bs, t0 + k * BEAT / 2, bass(f, BEAT / 2 * 0.95 if not last else 2.5) * (1 if k % 2 == 0 else 0.7))
        # ドラム(2 小節目から)
        if b >= 1 and not last:
            for k in range(4):
                add(drm, t0 + k * BEAT, kick(rng) * (1 if k in (0, 2) else 0.0))
                if k in (1, 3):
                    add(drm, t0 + k * BEAT, noise_hit(rng, 0.25, 0.06, 20) * 0.55)
            for k in range(8):
                add(hat, t0 + k * BEAT / 2, noise_hit(rng, 0.06, 0.015, 4) * (0.5 if k % 2 else 0.3))
        if b >= 1 and last:
            add(drm, t0, kick(rng))
        # メロディ(3 小節目から)
        if b >= 2:
            for pos, m in MELODY[b % 8]:
                add(mel, t0 + pos * BEAT / 2, bell(midi(m)) * rng.uniform(0.75, 1.0))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * reverb(norm(keys), 0.3) + 0.55 * norm(bs) + 0.6 * norm(drm) + 0.12 * norm(hat) + 0.28 * reverb(norm(mel), 0.4)
    mix *= env_ar(len(mix), 0.5, 2.5)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 66
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
