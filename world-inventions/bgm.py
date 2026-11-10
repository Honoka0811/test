# -*- coding: utf-8 -*-
"""明るいポップ系BGMを numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 120BPM / 王道進行(F→G→Em→Am)。キック・クラップ・ハイハット・ベース・裏打ちコード・マリンバ風アルペジオ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 120
BEAT = 60.0 / BPM
BAR = BEAT * 4

PROG = [  # (ルート, コード構成音) MIDI
    (41, [65, 69, 72, 76]),  # Fmaj7
    (43, [67, 71, 74, 77]),  # G7
    (40, [64, 67, 71, 74]),  # Em7
    (45, [69, 72, 76, 79]),  # Am7
]


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, t0, sig, g=1.0):
    s = int(t0 * SR); e = min(s + len(sig), len(buf))
    if e > s:
        buf[s:e] += sig[:e - s] * g


def tvec(d):
    return np.arange(int(d * SR)) / SR


def lowpass(x, a):
    """1次ローパス(a: 0..1, 小さいほど暗い)。IIR を打ち切った指数窓の畳み込みで近似"""
    n = int(min(len(x), 6 / a))
    k = a * (1 - a) ** np.arange(n)
    return np.convolve(x, k.astype(np.float32))[:len(x)]


def kick():
    t = tvec(0.35)
    f = 50 + 90 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)


def clap(rng):
    t = tvec(0.25)
    n = rng.standard_normal(len(t)).astype(np.float32)
    n = n - lowpass(n, 0.25)  # ハイパス
    env = np.exp(-t / 0.06) * (1 + 0.6 * np.exp(-((t - 0.012) / 0.004) ** 2))
    return n * env * 0.6


def hat(rng, d=0.05):
    t = tvec(d)
    n = rng.standard_normal(len(t)).astype(np.float32)
    n = n - lowpass(n, 0.5)
    return n * np.exp(-t / 0.015) * 0.5


def bass(f, d):
    t = tvec(d)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    env = np.minimum(1, t / 0.005) * np.exp(-t / 0.25)
    return (s * env).astype(np.float32)


def stab(notes, d=0.22):
    t = tvec(d)
    s = np.zeros_like(t)
    for m in notes:
        f = midi(m)
        for h, a in ((1, 1), (2, 0.45), (3, 0.25), (4, 0.12)):
            s += a * np.sin(2 * np.pi * f * h * t * (1 + 0.003 * (h - 1)))
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.08)
    return (s * env / len(notes)).astype(np.float32)


def marimba(f, d=0.6):
    t = tvec(d)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.18) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.03)
    return (s * np.minimum(1, t / 0.002)).astype(np.float32)


def pad(notes, d):
    t = tvec(d)
    s = np.zeros_like(t)
    for m in notes:
        for det in (-0.003, 0.003):
            s += np.sin(2 * np.pi * midi(m - 12) * (1 + det) * t)
    env = np.minimum(1, t / 0.4) * np.minimum(1, (d - t) / 0.4)
    return (s * env / len(notes)).astype(np.float32)


def echo(x, delay_s=BEAT * 0.75, g=0.3, n=3):
    y = x.copy(); d = int(delay_s * SR)
    for i in range(1, n + 1):
        y[d * i:] += x[:len(x) - d * i] * g ** i
    return y


def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR
    drums = np.zeros(n, np.float32); bas = np.zeros(n, np.float32)
    chords = np.zeros(n, np.float32); mel = np.zeros(n, np.float32); pads = np.zeros(n, np.float32)
    K, nb = kick(), int(np.ceil(total / BAR))
    # アルペジオのパターン(コード構成音インデックス, 16分位置)
    arp_pat = [(0, 0), (2, 2), (1, 4), (3, 6), (2, 8), (1, 10), (3, 12), (2, 14)]
    for b in range(nb):
        t0 = b * BAR
        root, notes = PROG[b % 4]
        intro = b < 2
        last = t0 + BAR > total - 2.5
        add(pads, t0, pad(notes, BAR + 0.3))
        for q in range(4):
            tb = t0 + q * BEAT
            if not intro or q in (0, 2):
                add(drums, tb, K, 1.0 if not intro else 0.6)
            if not intro and q in (1, 3):
                add(drums, tb, clap(rng), 0.7)
            for e in (0, 0.5):
                add(drums, tb + e * BEAT, hat(rng, 0.04 if e == 0 else 0.07), 0.35 if e == 0 else 0.5)
            # ベース: 8分でルート、4拍目裏はオクターブ上
            add(bas, tb, bass(midi(root), BEAT * 0.48))
            add(bas, tb + BEAT / 2, bass(midi(root + (12 if q == 3 else 0)), BEAT * 0.45), 0.8)
            # 裏打ちコード
            if not intro:
                add(chords, tb + BEAT / 2, stab(notes))
        if not intro and not last:
            for idx, pos in arp_pat:
                if rng.random() < 0.85:
                    add(mel, t0 + pos * BEAT / 4, marimba(midi(notes[idx] + 12)), rng.uniform(0.6, 1.0))
    norm = lambda x: x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.75 * norm(drums) + 0.6 * norm(bas) + 0.32 * norm(chords) + 0.38 * echo(norm(mel)) + 0.22 * norm(pads))
    mix = mix[:int(total * SR)]
    t = np.arange(len(mix)) / SR
    mix *= np.minimum(1, t / 0.3) * np.clip((total - t) / 2.5, 0, 1)
    # ソフトクリップで軽くまとめる
    mix = np.tanh(1.4 * mix / (np.max(np.abs(mix)) + 1e-9)) / np.tanh(1.4)
    return (mix * 0.9).astype(np.float32)


if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
