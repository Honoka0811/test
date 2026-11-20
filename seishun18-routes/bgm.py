# -*- coding: utf-8 -*-
"""旅番組風の明るいBGMをプログラムで合成する(外部音源不要・権利フリー)。
Cメジャー / 112BPM。進行 C-G-Am-F。エレピ風コード + ベース + 軽いキック/クラップ/シェイカー + グロッケン風メロディ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 112
BEAT = 60.0 / BPM
BAR = BEAT * 4
PROG = [[60, 64, 67, 72], [59, 62, 67, 71], [57, 60, 64, 69], [57, 60, 65, 69]]  # C G/B Am F
ROOTS = [36, 35, 33, 29]
PENTA = [72, 74, 76, 79, 81, 84]


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, t, sig):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]


def tone(f, dur, decay, harm=((1, 1.0), (2, 0.35), (3, 0.12)), att=0.004):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in harm)
    env = np.exp(-t / decay) * np.minimum(1, t / att)
    return (x * env).astype(np.float32)


def epiano(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * 14 * t) * 0.6 * np.exp(-t / 0.15)  # 軽いFMでベル感
    x = np.sin(2 * np.pi * f * t + mod) + 0.2 * np.sin(2 * np.pi * 2 * f * t)
    return (x * np.exp(-t / 0.9) * np.minimum(1, t / 0.006)).astype(np.float32)


def kick(dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)


def noise_hit(rng, dur, decay, smooth):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(smooth) / smooth, mode='same')  # 簡易ハイパス
    return (x * np.exp(-t / decay)).astype(np.float32)


def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y


def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.55), (2903, 0.5))) / 4
    return (1 - mix) * x + mix * wet


def generate(total, seed=18):
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR
    keys, bass, drums, mel = (np.zeros(n, np.float32) for _ in range(4))
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; ch = PROG[b % 4]; root = ROOTS[b % 4]
        # コード: 1拍目 + 2拍目裏 + 3拍目裏(シンコペーション)
        for off, v in ((0, 1.0), (1.5, 0.6), (2.5, 0.7)):
            for m in ch:
                add(keys, t0 + off * BEAT, epiano(midi(m), 1.4) * v)
        # ベース: 8分で ルート-ルート-5度-ルート…
        pat = [0, 0, 7, 0, 0, 12, 7, 0]
        for k, iv in enumerate(pat):
            add(bass, t0 + k * BEAT / 2, tone(midi(root + iv), 0.3, 0.12, ((1, 1), (2, 0.25))) * (1 if k % 2 == 0 else 0.7))
        # ドラム(2小節目から)
        if b >= 1:
            for k in range(4):
                if k in (0, 2): add(drums, t0 + k * BEAT, kick() * 0.9)
                if k in (1, 3): add(drums, t0 + k * BEAT, noise_hit(rng, 0.25, 0.05, 24) * 0.35)
            for k in range(8):
                add(drums, t0 + k * BEAT / 2, noise_hit(rng, 0.08, 0.015, 6) * (0.10 if k % 2 else 0.06))
        # メロディ(グロッケン風、4小節目以降・まばら)
        if b >= 2:
            for k in range(8):
                if rng.random() < (0.55 if k % 2 == 0 else 0.25):
                    m = PENTA[rng.integers(0, len(PENTA))]
                    if m % 12 in [(x % 12) for x in ch] or rng.random() < 0.4:
                        add(mel, t0 + k * BEAT / 2, tone(midi(m), 1.0, 0.35, ((1, 1), (2.76, 0.25), (5.4, 0.08))))

    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.45 * norm(keys) + 0.45 * norm(bass) + 0.55 * norm(drums) + 0.22 * reverb(norm(mel), 0.4)
    mix = reverb(mix, 0.12)[:int(total * SR)]
    m = len(mix); env = np.ones(m, np.float32)
    fi, fo = int(0.3 * SR), int(2.5 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    mix *= env
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)


if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 78
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
