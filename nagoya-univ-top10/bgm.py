# -*- coding: utf-8 -*-
"""明るいポップ系BGM(F メジャー、124BPM、F-C-Dm-B♭ 進行)を numpy だけで合成する。外部音源なし。
使い方: python3 bgm.py 秒数 出力.wav
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 124
BEAT = 60 / BPM
rng = np.random.default_rng(7)


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def env(n, a=0.005, d=0.25, s=0.0, r=0.05, length=None):
    t = np.arange(n) / SR
    e = np.minimum(t / a, 1) * (s + (1 - s) * np.exp(-t / d))
    rn = int(r * SR)
    if rn and n > rn:
        e[-rn:] *= np.linspace(1, 0, rn)
    return e


def add(buf, x, t):
    i = int(t * SR)
    if i >= len(buf):
        return
    x = x[:len(buf) - i]
    buf[i:i + len(x)] += x


# 1小節ごとのコード(ルート, 構成音)  F  C  Dm  B♭
CHORDS = [(53, [65, 69, 72]), (48, [64, 67, 72]), (50, [65, 69, 74]), (46, [65, 70, 74])]
# メロディ(16分単位の位置, 音, 長さ[16分]) 2小節パターン×2
MELODY = [
    [(0, 77, 2), (2, 76, 2), (4, 77, 2), (6, 79, 2), (8, 81, 4), (12, 79, 2), (14, 77, 2)],
    [(0, 76, 3), (3, 72, 3), (6, 74, 2), (8, 76, 4), (12, 79, 4)],
    [(0, 77, 2), (2, 74, 2), (4, 77, 2), (6, 81, 2), (8, 79, 3), (11, 77, 3), (14, 74, 2)],
    [(0, 74, 4), (4, 77, 2), (6, 79, 2), (8, 77, 6)],
]


def generate(total):
    n = int(total * SR) + SR
    drums = np.zeros(n, np.float32)
    bass = np.zeros(n, np.float32)
    keys = np.zeros(n, np.float32)
    lead = np.zeros(n, np.float32)
    bar = BEAT * 4
    s16 = BEAT / 4
    nbars = int(total / bar) + 2

    # 素材
    kn = int(0.35 * SR); kt = np.arange(kn) / SR
    kick = np.sin(2 * np.pi * (45 * kt + 90 * (1 - np.exp(-kt * 30)) / 30)) * np.exp(-kt * 9)
    hn = int(0.06 * SR)
    hat = np.diff(rng.standard_normal(hn + 1)).astype(np.float32) * env(hn, 0.001, 0.015) * 0.35
    cn = int(0.25 * SR)
    clap = rng.standard_normal(cn) * env(cn, 0.002, 0.06) * 0.35
    clap = np.convolve(clap, np.ones(4) / 4, mode='same')

    for b in range(nbars):
        t0 = b * bar
        root, notes = CHORDS[b % 4]
        intro = b < 1          # 最初の1小節はドラム抜き
        for beat in range(4):
            tb = t0 + beat * BEAT
            if not intro:
                add(drums, kick * 0.9, tb)
                if beat in (1, 3):
                    add(drums, clap, tb)
            for k in range(2):  # 裏拍ハット
                add(drums, hat * (1.0 if k else 0.5), tb + k * BEAT / 2)
        # ベース: 8分で ルート/オクターブ
        for e8 in range(8):
            f = midi(root - 12 + (12 if e8 % 4 == 3 else 0))
            ln = int(BEAT / 2 * 0.9 * SR); t = np.arange(ln) / SR
            w = np.sign(np.sin(2 * np.pi * f * t)) * 0.3 + np.sin(2 * np.pi * f * t)
            w = np.convolve(w, np.ones(24) / 24, mode='same')
            add(bass, w * env(ln, 0.004, 0.18, 0.4, 0.03) * 0.33, t0 + e8 * BEAT / 2)
        # キー: 16分アルペジオ(ベル系)
        arp = notes + [notes[1] + 12, notes[2] + 12, notes[1] + 12, notes[0] + 12, notes[2]]
        for i in range(16):
            if i % 2 and rng.random() < 0.35:
                continue
            f = midi(arp[i % len(arp)])
            ln = int(0.35 * SR); t = np.arange(ln) / SR
            w = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 18)
            add(keys, w * env(ln, 0.002, 0.12) * 0.11, t0 + i * s16)
        # パッド(柔らかいコード)
        ln = int(bar * SR); t = np.arange(ln) / SR
        pad = sum(np.sin(2 * np.pi * midi(m) * t * (1 + d)) for m in notes for d in (-0.002, 0.002))
        add(keys, pad * env(ln, 0.25, 9, 0.6, 0.3) * 0.022, t0)
        # リード(2小節目以降、ナレーションの邪魔にならない音量)
        if b >= 2:
            for pos, note, l16 in MELODY[b % 4]:
                ln = int(l16 * s16 * SR); t = np.arange(ln) / SR
                f = midi(note)
                vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / 0.2, 1)
                ph = 2 * np.pi * f * np.cumsum(vib) / SR
                w = np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
                add(lead, w * env(ln, 0.01, 0.3, 0.5, 0.04) * 0.07, t0 + pos * s16)

    # 簡易リバーブ(キー&リード)
    wet = keys + lead
    rev = np.zeros_like(wet)
    for dly, g in ((0.031, 0.35), (0.047, 0.3), (0.071, 0.25), (0.113, 0.2), (0.173, 0.15), (0.241, 0.1)):
        d = int(dly * SR)
        rev[d:] += wet[:-d] * g
    mix = drums * 0.55 + bass + keys + lead + rev * 0.5
    mix = mix[:int(total * SR)]
    fo = int(2.0 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)
    fi = int(0.05 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    return (mix / np.max(np.abs(mix)) * 0.9).astype(np.float32)


if __name__ == '__main__':
    total = float(sys.argv[1]); out = sys.argv[2]
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, len(x) / SR, 's')
