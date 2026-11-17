# -*- coding: utf-8 -*-
"""ショート動画用のBGMを numpy だけで合成する(外部音源不要・権利フリー)。
Aマイナー・ペンタトニック / 132BPM。四つ打ちキック + ハット + ベース + 琴風のプラック + パッド。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 132
BEAT = 60.0 / BPM
S16 = BEAT / 4

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, t, sig, gain=1.0):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if 0 <= s < e: buf[s:e] += sig[:e - s] * gain

def kick():
    n = int(0.32 * SR); t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t * 38)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)).astype(np.float32)
def taiko():
    n = int(1.1 * SR); t = np.arange(n) / SR
    f = 62 + 60 * np.exp(-t * 22)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
    x += np.random.default_rng(1).standard_normal(n) * np.exp(-t * 60) * 0.5
    return x.astype(np.float32)
def hat(rng, open_=False):
    n = int((0.14 if open_ else 0.045) * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n); x = x - np.concatenate([[0], x[:-1]])     # 高域だけ残す
    return (x * np.exp(-t * (22 if open_ else 90))).astype(np.float32)
def clap(rng):
    n = int(0.16 * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n); x = x - 0.6 * np.concatenate([[0], x[:-1]])
    return (x * (np.exp(-t * 30) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 400) * (t < 0.035))).astype(np.float32)
def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(4 * np.pi * f * t) + 0.2 * np.sin(6 * np.pi * f * t)
    env = np.minimum(t / 0.006, 1) * np.exp(-t * 5) * np.minimum((dur - t) / 0.02, 1)
    return (x * env).astype(np.float32)
def pluck(f, dur=0.5):                    # 琴っぽい減衰音
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (5 + 3.2 * k)) / k for k in range(1, 7))
    return (x * np.minimum(t / 0.003, 1)).astype(np.float32)
def pad(fs, dur):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for f in fs:
        for d in (-0.35, 0.35): x += np.sin(2 * np.pi * (f + d) * t) + 0.3 * np.sin(4 * np.pi * (f + d) * t)
    env = np.minimum(t / 0.25, 1) * np.minimum((dur - t) / 0.3, 1)
    return (x * env / len(fs)).astype(np.float32)

# 4小節ループ: Am - F - C - G
ROOTS = [45, 41, 48, 43]
CHORDS = [[57, 60, 64], [57, 60, 65], [55, 60, 64], [55, 59, 62]]
# 16分音符グリッド上のメロディ(Aマイナー・ペンタ)。None は休符
MEL = [
    [81, None, None, 79, None, 76, None, None, 72, None, 76, None, 79, None, None, None],
    [81, None, None, 79, None, 77, None, None, 72, None, 69, None, 72, None, None, None],
    [79, None, None, 76, None, 72, None, None, 76, None, 79, None, 84, None, None, None],
    [86, None, 83, None, 79, None, None, 74, None, 79, None, 83, 81, None, 79, None],
]
BASS_PAT = [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0]

def generate(dur, hits=()):
    """dur 秒のBGM。hits はシーン切り替えの時刻(和太鼓のアクセントを入れる)"""
    rng = np.random.default_rng(7)
    n = int(dur * SR)
    drums, low, lead, pd = (np.zeros(n + SR * 2, dtype=np.float32) for _ in range(4))
    K, TK = kick(), taiko()
    bar = 0; t0 = 0.0
    while t0 < dur:
        c = bar % 4; intro = bar < 2          # 最初の2小節はドラム控えめ
        add(pd, t0, pad([midi(m) for m in CHORDS[c]], BEAT * 4 + 0.2), 0.20)
        for i in range(16):
            t = t0 + i * S16
            if i % 4 == 0 and not intro: add(drums, t, K, 0.95)
            if i % 4 == 2: add(drums, t, hat(rng, open_=(i == 14)), 0.16)
            elif not intro: add(drums, t, hat(rng), 0.07)
            if i in (4, 12) and not intro: add(drums, t, clap(rng), 0.22)
            if BASS_PAT[i]: add(low, t, bass(midi(ROOTS[c] - 12 + (12 if i == 13 else 0)), S16 * 1.8), 0.5)
            m = MEL[c][i]
            if m and (bar >= 1): add(lead, t, pluck(midi(m)), 0.22); add(lead, t + S16 * 3, pluck(midi(m)), 0.06)   # 付点8分ディレイ
        bar += 1; t0 = bar * BEAT * 4
    for h in hits: add(drums, h, TK, 1.0)
    x = (drums + low + lead + pd)[:n]
    # 簡易リバーブ(リードとパッドのみ)
    wet = (lead + pd)[:n]; rv = np.zeros(n, dtype=np.float32)
    for d, gn in ((0.031, 0.5), (0.047, 0.4), (0.071, 0.3), (0.113, 0.22), (0.171, 0.15)):
        k = int(d * SR); rv[k:] += wet[:-k] * gn
    x += rv * 0.5
    x = np.tanh(x * 1.2)
    fade = int(1.5 * SR); x[-fade:] *= np.linspace(1, 0, fade) ** 1.5
    x[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    return (x / np.max(np.abs(x)) * 0.9).astype(np.float32)

if __name__ == '__main__':
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 52
    out = sys.argv[2] if len(sys.argv) > 2 else 'output/bgm.wav'
    x = generate(dur)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out)
