# -*- coding: utf-8 -*-
"""明るいポップ系BGMをプログラムで合成する(外部音源不要・権利フリー)。
Cメジャー / 118BPM / 王道進行(F→G→Em→Am)。キック・クラップ・ハイハット・ベース・裏打ちコード・ベルのアルペジオ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 118
BEAT = 60.0 / BPM
BAR = BEAT * 4

# 王道進行 IV-V-iii-vi(MIDIノート)
PROG = [
    [53, 57, 60, 64],  # Fmaj7
    [55, 59, 62, 65],  # G7
    [52, 55, 59, 62],  # Em7
    [57, 60, 64, 67],  # Am7
]
ROOTS = [41, 43, 40, 45]
# ベルのメロディ(1小節 8 個の 8 分音符、None は休符)。コードトーン中心
MEL = [
    [72, None, 76, 77, None, 76, 72, None],
    [74, None, 77, 79, None, 77, 74, 71],
    [71, None, 74, 76, None, 74, 71, None],
    [72, None, 76, 79, 81, None, 79, 76],
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig, g=1.0):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += g * sig[:e - s]

def lp(x, k):
    """移動平均による簡易ローパス"""
    return np.convolve(x, np.ones(k) / k, mode='same').astype(np.float32)

def kick(rng):
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def clap(rng):
    n = int(0.25 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n).astype(np.float32)
    nz = nz - lp(nz, 12)  # 高域寄りに
    env = np.exp(-t / 0.06) * (1 + 0.6 * (np.sin(2 * np.pi * 90 * t) > 0) * (t < 0.03))
    return (nz * env).astype(np.float32)

def hat(rng, dur=0.06):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n).astype(np.float32)
    nz = nz - lp(nz, 4)
    return (nz * np.exp(-t / 0.018)).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    env = np.minimum(1, t / 0.005) * np.exp(-t / 0.35)
    return (s * env).astype(np.float32)

def stab(freqs, dur):
    """裏打ちのコード(ノコギリ波を少しローパス)"""
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n, dtype=np.float32)
    for f in freqs:
        for det in (-0.003, 0.003):
            s += (2 * ((f * (1 + det) * t) % 1) - 1).astype(np.float32)
    s = lp(s, 10)
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.09)
    return (s * env).astype(np.float32)

def bell(f, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t / 0.15))
    return (s * np.minimum(1, t / 0.003) * np.exp(-t / 0.3)).astype(np.float32)

def pad(freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n, dtype=np.float32)
    for f in freqs:
        for h in (1, 2, 3):
            s += (1 / h ** 1.5) * np.sin(2 * np.pi * f * h * t).astype(np.float32)
    env = np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4)
    return (s * np.clip(env, 0, 1)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.55))) / 3
    return (1 - mix) * x + mix * wet

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    tr = {k: np.zeros(n, dtype=np.float32) for k in ('kick', 'clap', 'hat', 'bass', 'stab', 'bell', 'pad')}
    nbars = int(np.ceil(total / BAR)) + 1
    for b in range(nbars):
        t0 = b * BAR; i = b % 4
        chord = PROG[i]
        intro = b < 2            # 最初の 2 小節はドラム控えめ
        add(tr['pad'], t0, pad([midi(m) for m in chord], BAR + 0.1))
        for k in range(4):
            tb = t0 + k * BEAT
            if not intro or k == 0:
                add(tr['kick'], tb, kick(rng))
            if k in (1, 3) and not intro:
                add(tr['clap'], tb, clap(rng))
            # ベース: 8 分でルート/オクターブ
            for h in range(2):
                f = midi(ROOTS[i] + (12 if h else 0))
                add(tr['bass'], tb + h * BEAT / 2, bass(f, BEAT / 2 + 0.05), 1.0 if h == 0 else 0.7)
            add(tr['stab'], tb + BEAT / 2, stab([midi(m) for m in chord], 0.25))
        for h in range(8):
            add(tr['hat'], t0 + h * BEAT / 2, hat(rng), 1.0 if h % 2 else 0.5)
            m = MEL[i][h]
            if m is not None and b >= 2:
                add(tr['bell'], t0 + h * BEAT / 2, bell(midi(m)))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.85 * norm(tr['kick']) + 0.35 * norm(tr['clap']) + 0.16 * norm(tr['hat'])
           + 0.55 * norm(tr['bass']) + 0.22 * norm(tr['stab']) + 0.25 * reverb(norm(tr['bell']), 0.35)
           + 0.22 * norm(tr['pad']))
    mix = reverb(mix, 0.12)
    # 1 秒フェードイン、最後 2.5 秒フェードアウト
    env = np.ones(n, dtype=np.float32)
    fi, fo = int(1.0 * SR), int(2.5 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    mix *= env
    # 簡易ソフトクリップ
    mix = np.tanh(1.3 * mix / (np.max(np.abs(mix)) + 1e-9)) / np.tanh(1.3)
    return (mix * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
