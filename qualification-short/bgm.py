# -*- coding: utf-8 -*-
"""明るく軽いオフィス系ポップBGMを numpy だけで合成する(外部音源なし・権利フリー)。
F メジャー / 108BPM。進行 F - G - Em - Am - Dm - G - C - C(4小節×2)。
エレピ風コード + マリンバ風アルペジオ + プラックベース + 軽いキック/クラップ/シェイカー + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 108
BEAT = 60.0 / BPM
BAR = BEAT * 4

PROG = [  # (ベースのルート, コード構成音) MIDI
    (41, [57, 60, 64, 65]),  # Fmaj7
    (43, [55, 59, 62, 67]),  # G
    (40, [55, 59, 64, 67]),  # Em
    (45, [57, 60, 64, 69]),  # Am
    (38, [57, 60, 62, 65]),  # Dm
    (43, [55, 59, 62, 65]),  # G7
    (36, [55, 60, 64, 67]),  # C
    (36, [55, 60, 64, 72]),  # C
]


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, start, sig):
    s = int(start * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]


def epiano(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.exp(-t / 1.1) * (1 - np.exp(-t / 0.004))
    tine = np.exp(-t / 0.25)
    sig = np.sin(2 * np.pi * f * t + 0.6 * tine * np.sin(2 * np.pi * f * 2 * t))  # 軽いFMで鐘っぽさ
    sig += 0.25 * np.sin(2 * np.pi * f * 2 * t) * tine
    r = min(n, int(0.08 * SR)); env[-r:] *= np.linspace(1, 0, r)
    return (sig * env).astype(np.float32)


def marimba(f, dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.18) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.03)
    sig *= (1 - np.exp(-t / 0.002))
    return sig.astype(np.float32)


def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)
    env = np.exp(-t / 0.35) * (1 - np.exp(-t / 0.003))
    r = min(n, int(0.03 * SR)); env[-r:] *= np.linspace(1, 0, r)
    return (sig * env).astype(np.float32)


def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)


def noise_hit(rng, dur, decay, hp=True):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    if hp: x = np.diff(x, prepend=0)  # 簡易ハイパス
    return (x * np.exp(-t / decay)).astype(np.float32)


def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y


def reverb(x, mix):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.55), (2617, 0.52))) / 4
    return (1 - mix) * x + mix * wet


def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    keys, mar, bas, drm = (np.zeros(n, np.float32) for _ in range(4))
    ARP = [0, 2, 1, 3, 2, 1, 3, 2]
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR
        root, chord = PROG[b % 8]
        # エレピ: 1拍目と 2.5拍目にコード
        for off, vel in ((0, 1.0), (1.5 * BEAT, 0.6), (3 * BEAT, 0.5)):
            for m in chord:
                add(keys, t0 + off, epiano(midi(m), 1.6) * vel)
        # マリンバ: 8分のアルペジオ(イントロ 2 小節は休み)
        if b >= 2:
            for k in range(8):
                m = chord[ARP[k]] + 12
                add(mar, t0 + k * BEAT / 2, marimba(midi(m)) * (1.0 if k % 2 == 0 else 0.7))
        # ベース: 8分で ルート-ルート-5度…
        for k, iv in enumerate([0, 0, 12, 0, 7, 0, 12, 7]):
            add(bas, t0 + k * BEAT / 2, bass(midi(root + iv), BEAT / 2 * 0.9) * (1.0 if k % 2 == 0 else 0.75))
        # ドラム(1 小節目から): キック 1,3 拍 + 裏、クラップ 2,4 拍、シェイカー 16分
        if b >= 1:
            for k in (0, 2, 2.5):
                add(drm, t0 + k * BEAT, kick() * (1.0 if k != 2.5 else 0.6))
            for k in (1, 3):
                add(drm, t0 + k * BEAT, noise_hit(rng, 0.25, 0.05) * 0.35)
            for k in range(16):
                add(drm, t0 + k * BEAT / 4, noise_hit(rng, 0.06, 0.012) * (0.12 if k % 2 else 0.06))

    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.45 * reverb(norm(keys), 0.35) + 0.32 * reverb(norm(mar), 0.25) + 0.55 * norm(bas) + 0.5 * norm(drm)
    env = np.ones(n, np.float32)
    fi, fo = int(0.5 * SR), int(2.5 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    mix *= env
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)


if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
