# -*- coding: utf-8 -*-
"""やさしいLo-fi風BGMを numpy だけで合成する(外部音源なし・権利フリー)。
Fメジャー / 82BPM。エレピ風コード + ベース + やわらかいキック/スネア/ハイハット + ベル風メロディ + うっすらレコードノイズ。
冒頭〜約19秒(悩みのパート)はコードだけ、そこからビートが入り、最後はフェードアウト。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 82
BEAT = 60.0 / BPM
BAR = BEAT * 4
BEAT_IN = 19.0  # ビートが入る時刻(「会話は共同作業」のシーン)

# Fmaj7 - Em7 - Dm7 - Cmaj7 / Bbmaj7 - Am7 - Gm7 - C7sus4
PROG = [
    [53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59],
    [46, 50, 53, 57], [45, 48, 52, 55], [43, 46, 50, 53], [48, 53, 55, 58],
]
ROOTS = [41, 40, 38, 36, 34, 33, 31, 36]
# ベル風メロディ(8小節分, (拍, MIDI, 拍数))
MELODY = [
    (0, 72, 1.5), (1.5, 69, 0.5), (2, 67, 2),
    (4, 71, 1), (5, 67, 1), (6, 64, 2),
    (8, 69, 1.5), (9.5, 65, 0.5), (10, 64, 1), (11, 62, 1),
    (12, 64, 3),
    (16, 65, 1.5), (17.5, 62, 0.5), (18, 65, 2),
    (20, 64, 1), (21, 60, 1), (22, 64, 2),
    (24, 62, 1.5), (25.5, 65, 0.5), (26, 70, 2),
    (28, 67, 3),
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, t, sig):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def epiano(f, dur, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.exp(-t / 1.6) * np.minimum(1, t / 0.006)
    rel = np.ones(n); r = min(int(0.25 * SR), n); rel[-r:] = np.linspace(1, 0, r)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.2 * t)
    sig = np.sin(2 * np.pi * f * t + 0.6 * np.exp(-t / 0.3) * np.sin(2 * np.pi * f * t))  # 軽いFMで「チン」と鳴らす
    sig += 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.5)
    return (sig * env * rel * trem * vel).astype(np.float32)

def bell(f, dur):
    n = int((dur + 1.2) * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t + 1.2 * np.exp(-t / 0.4) * np.sin(2 * np.pi * 3.5 * f * t))
    return (sig * np.exp(-t / 0.9) * np.minimum(1, t / 0.004)).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.minimum(1, t / 0.01) * np.exp(-t / 1.2)
    rel = np.ones(n); r = min(int(0.1 * SR), n); rel[-r:] = np.linspace(1, 0, r)
    return ((np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t)) * env * rel).astype(np.float32)

def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)).astype(np.float32)

def snare(rng):
    n = int(0.3 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = np.convolve(nz, np.ones(6) / 6, mode='same')
    return ((0.6 * nz * np.exp(-t / 0.07) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05))).astype(np.float32)

def hat(rng, open_=False):
    n = int(0.12 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = nz - np.convolve(nz, np.ones(4) / 4, mode='same')  # 高域だけ
    return (nz * np.exp(-t / (0.05 if open_ else 0.018))).astype(np.float32)

def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y

def reverb(x, mix):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (2711, 0.64))) / 4
    return (1 - mix) * x + mix * wet

def lowpass(x, a):
    """指数平滑(1次ローパス)を有限長カーネルの畳み込みで近似。a が小さいほど暗い音"""
    k = np.exp(-np.arange(int(5 / a)) * a); k /= k.sum()
    return np.convolve(x, k, mode='full')[:len(x)].astype(np.float32)

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    keys = np.zeros(n, np.float32); bs = np.zeros(n, np.float32)
    drums = np.zeros(n, np.float32); mel = np.zeros(n, np.float32)
    nbars = int(np.ceil(total / BAR)) + 1
    for b in range(nbars):
        t0 = b * BAR; ch = PROG[b % 8]
        # エレピ: 1拍目と「3拍目の裏」に少しずらして(ストラム)
        for hit, vel in ((0, 1.0), (2.5, 0.6)):
            for i, m in enumerate(ch):
                add(keys, t0 + hit * BEAT + i * 0.012 + rng.uniform(0, 0.006), epiano(midi(m), BAR - hit * BEAT + 0.3, vel * 0.8))
        if t0 + 0.01 >= BEAT_IN - BAR * 0.5:
            r = midi(ROOTS[b % 8])
            add(bs, t0, bass(r, BEAT * 2.5))
            add(bs, t0 + 2.5 * BEAT, bass(r * (1.5 if b % 2 else 1), BEAT * 1.5) * 0.8)
        if t0 >= BEAT_IN:
            sw = BEAT / 2 * 0.12  # ハネ(スウィング)
            add(drums, t0, kick()); add(drums, t0 + 2.5 * BEAT, kick() * 0.7)
            add(drums, t0 + BEAT, snare(rng) * 0.55); add(drums, t0 + 3 * BEAT, snare(rng) * 0.55)
            for k in range(8):
                add(drums, t0 + k * BEAT / 2 + (sw if k % 2 else 0), hat(rng, k == 7) * (0.22 if k % 2 else 0.32))
    # メロディ(8小節フレーズ)をビート開始 4 小節後から繰り返し
    first = int(np.ceil(BEAT_IN / BAR)) * BAR + BAR * 4
    t = first
    while t < total:
        for beat, m, d in MELODY:
            add(mel, t + beat * BEAT, bell(midi(m), d * BEAT))
        t += BAR * 8

    noise = rng.standard_normal(n).astype(np.float32)
    noise = lowpass(noise, 0.02) * 0.6
    crackle = (rng.random(n) < 0.00025).astype(np.float32) * rng.uniform(-1, 1, n).astype(np.float32)

    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.55 * norm(keys) + 0.45 * norm(bs) + 0.5 * norm(drums)
           + 0.32 * reverb(norm(mel), 0.35) + 0.02 * norm(noise) + 0.04 * crackle)
    mix = reverb(lowpass(mix, 0.7), 0.14)
    mix = mix - lowpass(mix, 0.005)  # 40Hz 以下の不要な超低域をカット
    env = np.ones(n, np.float32)
    fi, fo = int(1.5 * SR), int(4.0 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    mix *= env
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 66
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
