# -*- coding: utf-8 -*-
"""SF っぽいシンセウェーブ風 BGM を numpy だけで合成する(外部音源不要・権利フリー)。
Aマイナー / 112BPM。キック + ハイハット + クラップ + 16分のシンセベース + パッド + きらきらしたアルペジオ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 112
BEAT = 60.0 / BPM
BAR = BEAT * 4
S16 = BEAT / 4

# Am - F - C - G (4小節ループ)
PROG = [
    (45, [57, 60, 64, 69]),   # Am
    (41, [57, 60, 65, 69]),   # F
    (48, [55, 60, 64, 67]),   # C
    (43, [55, 59, 62, 67]),   # G
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(round(start_s * SR)); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def fade(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: env[:na] = np.linspace(0, 1, na)
    if nr: env[n - nr:] = np.linspace(1, 0, nr)
    return env

def lowpass(x, alpha):
    """1次ローパス(alpha が小さいほど暗い)。短い音にだけ使う"""
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc); y[i] = acc
    return y

def kick():
    n = int(0.32 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)).astype(np.float32)

def hat(rng, dur=0.05):
    n = int(dur * 4 * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(12) / 12, mode='same')   # ハイパス
    return x * np.exp(-t / dur)

def clap(rng):
    n = int(0.25 * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = np.convolve(x, np.ones(6) / 6, mode='same') - np.convolve(x, np.ones(60) / 60, mode='same')
    env = sum(np.exp(-np.clip(t - d, 0, None) / 0.05) * (t >= d) for d in (0, 0.011, 0.023))
    return x * env / 3

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    saw = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 9))
    return (saw * np.exp(-t / (dur * 0.6)) * fade(n, 0.004, 0.02)).astype(np.float32)

def pad(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.005, 0, 0.005):
        for h in (1, 2, 3, 4):
            sig += (1 / h ** 1.5) * np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6.28))
    return sig

def bell(f, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t + 1.6 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.15))   # 軽い FM
    return (x * np.exp(-t / 0.22) * fade(n, 0.003, 0.05)).astype(np.float32)

def echo(x, delay_s, g, repeats=4):
    y = x.copy(); d = int(delay_s * SR)
    for k in range(1, repeats + 1):
        y[k * d:] += (g ** k) * x[:len(x) - k * d]
    return y

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR) + 1
    drums = np.zeros(n, np.float32); bs = np.zeros(n, np.float32)
    pd = np.zeros(n, np.float32); arp = np.zeros(n, np.float32)
    K, C = kick(), clap(rng)
    ARP = [0, 1, 2, 3, 2, 1, 2, 3]
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; root, chord = PROG[b % 4]
        intro = b < 2                      # 最初の2小節はパッドとアルペジオだけ
        # パッド
        sig = sum(pad(midi(m), BAR + 0.4, rng) for m in chord)
        add(pd, t0, sig * fade(len(sig), 0.25, 0.4))
        for s in range(16):
            ts = t0 + s * S16
            if not intro:
                if s % 4 == 0: add(drums, ts, K)
                if s % 8 == 4: add(drums, ts, C * 0.8)
                if s % 2 == 0: add(drums, ts, hat(rng) * (0.22 if s % 4 == 2 else 0.11))
                # 16分のオクターブベース
                add(bs, ts, bass(midi(root - 12 + (12 if s % 2 else 0)), S16 * 0.95) * (0.6 if s % 4 == 0 else 1.0))
            if s % 2 == 0:
                add(arp, ts, bell(midi(chord[ARP[(s // 2) % 8]] + 12)) * (0.9 if s % 4 == 0 else 0.6))
        if b % 4 == 3 and not intro:       # 4小節ごとのフィル
            for k in range(4):
                add(drums, t0 + BAR - (4 - k) * S16, C * (0.35 + 0.15 * k))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    # サイドチェイン風: キックの位置でベースとパッドを少し凹ませる
    tt = np.arange(n) / SR
    pump = 1 - 0.45 * np.exp(-((tt % BEAT) / 0.12))
    pump[tt < 2 * BAR] = 1
    mix = (0.85 * norm(drums) + 0.50 * norm(bs) * pump + 0.38 * norm(pd) * pump
           + 0.30 * echo(norm(arp), BEAT * 0.75, 0.45))
    mix *= fade(len(mix), 0.3, 2.5)
    mix = np.tanh(mix * 1.2)                      # 軽いサチュレーション
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
