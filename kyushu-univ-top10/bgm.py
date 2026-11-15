# -*- coding: utf-8 -*-
"""明るいポップ系BGMを numpy だけで合成する(外部音源なし・権利フリー)。
C メジャー / 128 BPM、王道進行 F→G→Em→Am。キック・クラップ・ハイハット・ベース・
裏打ちコード・ベルのアルペジオ。使い方: python3 bgm.py 秒数 出力.wav"""
import sys, wave
import numpy as np

SR = 48000
BPM = 128
BEAT = 60 / BPM
rng = np.random.default_rng(7)

def hz(m): return 440 * 2 ** ((m - 69) / 12)

# 王道進行(1小節ずつ):F, G, Em, Am  各コードの構成音(MIDI)
PROG = [(53, [65, 69, 72]), (55, [67, 71, 74]), (52, [64, 67, 71]), (57, [69, 72, 76])]

def env(n, a=0.005, d=0.25):
    t = np.arange(n) / SR
    e = np.exp(-t / d)
    k = int(a * SR)
    if k: e[:k] *= np.linspace(0, 1, k)
    return e

def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    out = 0
    for dt in (-detune, 0, detune):
        ph = (t * f * (1 + dt)) % 1
        out = out + (2 * ph - 1)
    return out / 3

def lowpass(x, a):
    # 1 次ローパス(ベクトル化のため簡易に移動平均で近似)
    k = max(1, int(a))
    return np.convolve(x, np.ones(k) / k, mode='same')

def kick(n):
    t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)

def clap(n):
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t * 22)
    return x - lowpass(x, 6)

def hat(n):
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    return (x - lowpass(x, 3)) * np.exp(-t * 60)

def bell(f, n):
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.01 * t)
            + 0.12 * np.sin(2 * np.pi * f * 3.98 * t)) * np.exp(-t * 4.5)

def generate(seconds):
    N = int(seconds * SR) + SR
    L = np.zeros(N, np.float32); R = np.zeros(N, np.float32)
    def add(x, t0, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= N: return
        x = x[:N - i] * gain
        L[i:i + len(x)] += x * (1 - pan) ** 0.5 * 1.0
        R[i:i + len(x)] += x * (1 + pan) ** 0.5 * 1.0

    k = kick(int(0.35 * SR)); c = clap(int(0.25 * SR)); h = hat(int(0.06 * SR))
    nbeats = int(seconds / BEAT) + 1
    melody = [0, 1, 2, 1, 2, 3, 2, 1]  # コード音を上下するアルペジオ
    for b in range(nbeats):
        t0 = b * BEAT
        bar = b // 4
        root, chord = PROG[bar % 4]
        intro = bar < 1                      # 最初の 1 小節はドラム控えめ
        add(k, t0, 0.9 if not intro else 0.0)
        if b % 2 == 1: add(c, t0, 0.32 if not intro else 0.0)
        add(h, t0 + BEAT / 2, 0.18, 0.3)
        add(h, t0 + BEAT / 4 * 3, 0.07, -0.3)
        # ベース:8 分でルート→オクターブ
        for j, m in enumerate((root - 12, root)):
            n = int(BEAT / 2 * SR)
            x = lowpass(saw(hz(m), n, 0.002), 10) * env(n, 0.004, 0.18)
            add(x, t0 + j * BEAT / 2, 0.30)
        # 裏打ちコード(プラック)
        n = int(BEAT * 0.45 * SR)
        st = sum(saw(hz(m), n, 0.006) for m in chord) / len(chord)
        add(lowpass(st, 4) * env(n, 0.003, 0.09), t0 + BEAT / 2, 0.22, 0.15)
        # ベルのアルペジオ(16 分 × 2)
        if not intro:
            for j in range(2):
                idx = melody[(b * 2 + j) % len(melody)]
                m = (chord + [chord[0] + 12])[idx] + 12
                add(bell(hz(m), int(0.6 * SR)), t0 + j * BEAT / 2, 0.075, -0.4 + 0.8 * (idx / 3))
    # 簡易リバーブ(多タップディレイ)
    for d, g in ((0.031, 0.25), (0.053, 0.2), (0.089, 0.15), (0.137, 0.1)):
        s = int(d * SR)
        L[s:] += R[:-s] * g; R[s:] += L[:-s] * g * 0.9
    out = np.stack([L, R], 1)[:int(seconds * SR)]
    # 末尾 1.5 秒でフェードアウト
    f = int(1.5 * SR)
    out[-f:] *= np.linspace(1, 0, f)[:, None]
    return (out / np.max(np.abs(out)) * 0.9).astype(np.float32)

if __name__ == '__main__':
    sec = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    path = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(sec)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', path)
