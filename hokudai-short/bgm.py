# -*- coding: utf-8 -*-
"""明るいポップ調のBGMを numpy だけで合成する(外部音源なし・権利フリー)。
F メジャー / 118BPM。キック + クラップ + ハイハット + ベース + プラック和音 + ベルのアルペジオ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 118
BEAT = 60.0 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(7)

# F - C - Dm - Bb (I-V-vi-IV)
CHORDS = [[65, 69, 72], [64, 67, 72], [62, 65, 69], [62, 65, 70]]
ROOTS = [41, 36, 38, 34]
# ベルのフレーズ(8分音符16個 / 1小節 = 8個)。None は休符
MELODY = [
    [77, None, 81, 79, 77, None, 72, None],
    [76, None, 79, None, 76, 74, 72, None],
    [74, None, 77, 76, 74, None, 69, None],
    [70, 72, 74, None, 77, None, 76, None],
]


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, t, sig, g=1.0):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * g


def tt(d): return np.arange(int(d * SR)) / SR


def kick():
    t = tt(0.35)
    f = 50 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def lowpass(x, fc):
    """一次ローパス(短い打楽器用なので素朴なループで十分)"""
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc; y[i] = acc
    return y


def clap():
    t = tt(0.25)
    n = lowpass(rng.standard_normal(len(t)), 2500)
    env = np.exp(-t * 22) + 0.6 * np.exp(-((t - 0.012) * 300) ** 2)
    return n * env * 0.5


def hat(open_=False):
    t = tt(0.12 if not open_ else 0.25)
    n = np.diff(rng.standard_normal(len(t)), prepend=0)
    n = lowpass(n, 9000)
    return n * np.exp(-t * (60 if not open_ else 18)) * 0.035


def bass(n, d):
    t = tt(d)
    f = midi(n)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(1, t / 0.005) * np.exp(-t * 3) * np.minimum(1, (d - t) / 0.02)
    return x * env * 0.30


def pluck(n, d):
    t = tt(d)
    f = midi(n)
    x = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (6 + 5 * k)) / k for k in range(1, 6))
    return x * np.minimum(1, t / 0.003) * 0.24


def bell(n, d):
    t = tt(d)
    f = midi(n)
    x = np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t * 6))
    return x * np.minimum(1, t / 0.002) * np.exp(-t * 4.5) * 0.26


def pad(chord, d):
    t = tt(d)
    x = sum(np.sin(2 * np.pi * midi(n - 12) * t * (1 + dt)) for n in chord for dt in (-0.003, 0.003))
    env = np.minimum(1, t / 0.4) * np.minimum(1, (d - t) / 0.4)
    return x * env * 0.025


def generate(total):
    buf = np.zeros(int((total + 2) * SR), dtype=np.float32)
    nbars = int(np.ceil(total / BAR))
    K, C, H, HO = kick(), clap(), hat(), hat(True)
    for b in range(nbars):
        t0 = b * BAR
        ci = b % 4
        intro = b < 1
        add(buf, t0, pad(CHORDS[ci], BAR + 0.3))
        for q in range(4):
            tb = t0 + q * BEAT
            if not intro:
                add(buf, tb, K, 0.55)
                if q in (1, 3): add(buf, tb, C)
            for e in range(2):
                add(buf, tb + e * BEAT / 2, HO if e == 1 and q == 3 else H, 1.0 if e else 0.6)
            # ベース: 8分で刻む
            for e in range(2):
                add(buf, tb + e * BEAT / 2, bass(ROOTS[ci] + (12 if e == 1 and q == 3 else 0), BEAT / 2 - 0.01))
            # 和音: 裏拍プラック
            for n in CHORDS[ci]:
                add(buf, tb + BEAT / 2, pluck(n, 0.5))
        if b >= 2 and (b // 4) % 2 == 0 or b % 8 in (5, 7):  # メロディは出入りさせて単調さを避ける
            for e, n in enumerate(MELODY[ci]):
                if n is not None:
                    add(buf, t0 + e * BEAT / 2, bell(n, 0.9))
    # 簡易ステレオ感の代わりに短いディレイで広がりを付ける
    d = int(BEAT * 0.75 * SR)
    wet = np.zeros_like(buf); wet[d:] = buf[:-d] * 0.18
    buf = buf + wet
    buf = buf[:int(total * SR)]
    # フェードイン / アウト
    fi, fo = int(0.3 * SR), int(2.0 * SR)
    buf[:fi] *= np.linspace(0, 1, fi); buf[-fo:] *= np.linspace(1, 0, fo)
    return (buf / (np.max(np.abs(buf)) or 1) * 0.9).astype(np.float32)


if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out)
