# -*- coding: utf-8 -*-
"""明るいトリビア動画向けのBGMをプログラムで合成する(外部音源不要・権利フリー)。
Cメジャー / 112BPM。カリンバ風のアルペジオ + 柔らかいベース + 軽いキック/シェイカー/クラップ + 薄いパッド + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 112
BEAT = 60.0 / BPM
BAR = BEAT * 4

# コード進行(MIDIノート)。4小節でループ: C - G - Am - F
PROG = [
    [60, 64, 67, 72],  # C
    [55, 59, 62, 67],  # G
    [57, 60, 64, 69],  # Am
    [53, 57, 60, 65],  # F
]
ROOTS = [48, 43, 45, 41]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def kalimba(f, dur=0.9):
    """カリンバ風: 基音 + 弱い倍音、速い減衰"""
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.exp(-t / 0.28) * (1 - np.exp(-t / 0.003))
    return ((np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.12)
             + 0.12 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.06)) * env).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.minimum(1, t / 0.01) * np.exp(-t / (dur * 0.9))
    return ((np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 2 * f * t)) * env).astype(np.float32)

def kick(dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 42 + 90 * np.exp(-t / 0.035)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(phase) * np.exp(-t / 0.12)).astype(np.float32)

def shaker(rng, dur=0.08, bright=True):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(8) / 8, mode='same')   # 低域を落として「シャカ」に
    return (x * np.exp(-t / (0.018 if bright else 0.03)) * 0.5).astype(np.float32)

def clap(rng, dur=0.25):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = np.convolve(x, np.ones(6) / 6, mode='same')
    env = np.exp(-t / 0.05) + 0.6 * np.exp(-np.maximum(t - 0.012, 0) / 0.05) + 0.4 * np.exp(-np.maximum(t - 0.024, 0) / 0.08)
    return (x * env * 0.35).astype(np.float32)

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.003, 0.003):
        for h in range(1, 5):
            sig += (1 / h ** 2) * np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6.28))
    env = np.ones(n, dtype=np.float32)
    a = min(int(0.4 * SR), n); r = min(int(0.4 * SR), n)
    env[:a] = np.linspace(0, 1, a); env[n - r:] = np.minimum(env[n - r:], np.linspace(1, 0, r))
    return sig * env

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.22):
    wet = sum(comb(x, d, g) for d, g in ((1103, 0.66), (1427, 0.64), (1783, 0.62), (7919, 0.35))) / 4
    return (1 - mix) * x + mix * wet

# アルペジオのパターン(コード構成音のインデックス、8分音符×8)
PATTERNS = [
    [0, 2, 1, 3, 0, 2, 1, 3],
    [0, 1, 2, 3, 2, 1, 2, 3],
    [3, 2, 1, 0, 3, 2, 1, 0],
    [0, 2, 3, 2, 0, 2, 3, 4],
]

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    arp = np.zeros(n, dtype=np.float32); bas = np.zeros(n, dtype=np.float32)
    drums = np.zeros(n, dtype=np.float32); pad = np.zeros(n, dtype=np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        chord = PROG[b % 4]; root = ROOTS[b % 4]
        t0 = b * BAR
        pat = PATTERNS[(b // 4) % len(PATTERNS)]
        # アルペジオ(8分音符)
        for k in range(8):
            idx = pat[k]
            note = chord[idx % 4] + 12 * (idx // 4) + (12 if (b // 8) % 2 else 0)
            vel = 0.9 if k % 2 == 0 else 0.6
            add(arp, t0 + k * BEAT / 2, kalimba(midi(note)) * vel)
        # ベース: 1拍目と3拍目、2拍目の裏に軽く
        add(bas, t0, bass(midi(root), BEAT * 1.6))
        add(bas, t0 + BEAT * 1.5, bass(midi(root), BEAT * 0.45) * 0.6)
        add(bas, t0 + BEAT * 2, bass(midi(root + (7 if b % 2 else 0)), BEAT * 1.6))
        # ドラム
        for beat in (0, 2):
            add(drums, t0 + beat * BEAT, kick() * 0.9)
        add(drums, t0 + BEAT * 2.5, kick() * 0.5)
        for beat in (1, 3):
            add(drums, t0 + beat * BEAT, clap(rng))
        for k in range(8):
            add(drums, t0 + k * BEAT / 2, shaker(rng, bright=(k % 2 == 0)) * (0.5 if k % 2 == 0 else 0.3))
        # パッド(2小節ごとに薄く)
        if b % 2 == 0:
            for nn in chord:
                add(pad, t0, pad_note(midi(nn), BAR * 2.05, rng) * 0.06)
    mix = 0.55 * reverb(arp, 0.28) + 0.5 * bas + 0.45 * drums + pad
    # フェードイン/アウト
    fi = int(0.5 * SR); fo = min(int(2.0 * SR), n)
    mix[:fi] *= np.linspace(0, 1, fi); mix[n - fo:] *= np.linspace(1, 0, fo)
    mix = mix[:n]
    return (mix / (np.max(np.abs(mix)) or 1) * 0.8).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{total}s')
