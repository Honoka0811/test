# -*- coding: utf-8 -*-
"""軽快なローファイ・ポップ風BGMを numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 98BPM。I–V–vi–IV のエレピ和音 + ベース + キック/クラップ/ハット + ペンタトニックの短いフレーズ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 98
BEAT = 60.0 / BPM
BAR = BEAT * 4
PROG = [[60, 64, 67, 71], [55, 59, 62, 67], [57, 60, 64, 67], [53, 57, 60, 64]]  # Cmaj7 G Am F(add9風)
ROOTS = [36, 43, 45, 41]
PENTA = [72, 74, 76, 79, 81, 84]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, t, sig):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def epiano(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.exp(-t / 0.9) * (1 - np.exp(-t / 0.004))
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    sig = np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.3))
    return (sig * env * trem).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.minimum(1, t / 0.01) * np.exp(-t / 0.5)
    return ((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * env).astype(np.float32)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def noise_hit(rng, dur, decay, hp):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    if hp:  # 簡易ハイパス(差分)
        x = np.diff(x, prepend=0)
    return x * np.exp(-t / decay).astype(np.float32)

def bell(f, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.1)) * np.exp(-t / 0.25)).astype(np.float32)

def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y

def reverb(x, mix):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.56))) / 3
    return (1 - mix) * x + mix * wet

def lowpass(x, k=6):
    return np.convolve(x, np.ones(k) / k, mode='same').astype(np.float32)

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR
    keys, bs, drums, mel = (np.zeros(n, np.float32) for _ in range(4))
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; ch = PROG[b % 4]
        # エレピ: 1拍目と 2.5 拍目に和音(少しずらしてストラム)
        for off, vel in ((0, 1.0), (2.5 * BEAT, 0.6)):
            for i, m in enumerate(ch):
                add(keys, t0 + off + i * 0.012, epiano(midi(m), 1.8) * vel * 0.5)
        # ベース
        r = midi(ROOTS[b % 4])
        add(bs, t0, bass(r, BEAT * 1.5)); add(bs, t0 + 1.5 * BEAT, bass(r, BEAT) * 0.7)
        add(bs, t0 + 2.5 * BEAT, bass(r * 1.5, BEAT * 1.4) * 0.8)
        # ドラム(最初の 1 小節はイントロとしてハットのみ)
        for k in range(8):
            add(drums, t0 + k * BEAT / 2 + (0.018 if k % 2 else 0), noise_hit(rng, 0.06, 0.012, True) * (0.22 if k % 2 else 0.32))
        if b >= 1:
            add(drums, t0, kick()); add(drums, t0 + 2.5 * BEAT, kick() * 0.8)
            for k in (1, 3):
                add(drums, t0 + k * BEAT, lowpass(noise_hit(rng, 0.18, 0.05, False), 4) * 0.55)
        # メロディ(2 小節目以降、ペンタトニックで短いフレーズ)
        if b >= 2:
            for k in range(8):
                if rng.random() < (0.5 if k % 2 == 0 else 0.25):
                    add(mel, t0 + k * BEAT / 2, bell(midi(PENTA[rng.integers(0, len(PENTA))])) * rng.uniform(0.5, 0.9))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.5 * reverb(norm(keys), 0.3) + 0.55 * norm(lowpass(bs, 8)) + 0.6 * norm(drums) + 0.22 * reverb(norm(mel), 0.45)
    # ローファイ感: 軽いハイカット + ごく小さなノイズ
    mix = lowpass(mix, 3) + 0.004 * rng.standard_normal(len(mix)).astype(np.float32)
    mix = mix[:int(total * SR)]
    env = np.ones(len(mix), np.float32)
    fi, fo = int(0.8 * SR), int(3.0 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    mix *= env
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 55
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
