# -*- coding: utf-8 -*-
"""BGM をプログラムで合成する(外部音源不要・権利フリー)。
Cメジャー系 / 84BPM のゆったりしたローファイ風。エレピ風コード + ベース + やわらかいキック/ハット + ベル風メロディ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 84
BEAT = 60.0 / BPM
BAR = BEAT * 4
# Fmaj7 - Em7 - Dm7 - Cmaj7 / Fmaj7 - G6 - Am7 - Am7
PROG = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59],
        [53, 57, 60, 64], [55, 59, 62, 64], [57, 60, 64, 67], [57, 60, 64, 67]]
MELODY = [[76, None, 72, 69], [71, None, 67, None], [69, 72, None, 65], [67, None, 64, None],
          [72, None, 76, 77], [74, None, 71, None], [72, 76, None, 79], [76, None, None, None]]

def hz(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, t, sig):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def epiano(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    mod = 1.6 * np.exp(-t / 0.25) * np.sin(2 * np.pi * f * 2 * t)      # FM で立ち上がりだけ明るく
    env = np.minimum(t / 0.008, 1) * np.exp(-t / (dur * 0.45))
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.2 * t)
    return (np.sin(2 * np.pi * f * t + mod) * env * trem).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.minimum(t / 0.01, 1) * np.exp(-t / (dur * 0.6))
    return ((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env).astype(np.float32)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 42 + 70 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def hat(rng, dur=0.06):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(8) / 8, mode='same')                # 簡易ハイパス
    return x * np.exp(-t / 0.018)

def snare(rng):
    n = int(0.22 * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = np.convolve(x, np.ones(6) / 6, mode='same')
    return (x * np.exp(-t / 0.06) + 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)).astype(np.float32)

def bell(f, dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.15))
            * np.minimum(t / 0.004, 1) * np.exp(-t / 0.45)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y
def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (2671, 0.64))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    keys = np.zeros(n, np.float32); low = np.zeros(n, np.float32)
    drums = np.zeros(n, np.float32); lead = np.zeros(n, np.float32)
    sw = BEAT * 0.08                                                   # 裏拍を少し遅らせるスウィング
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; ch = PROG[b % 8]; full = b >= 2                  # 最初の2小節はエレピだけ
        for hit, (bt, dur) in enumerate(((0, 2.4), (2.5, 1.4))):
            for i, note in enumerate(ch):
                add(keys, t0 + bt * BEAT + i * 0.012, epiano(hz(note), dur * BEAT) * (0.22 if hit == 0 else 0.15))
        if full:
            root = hz(ch[0] - 12)
            add(low, t0, bass(root, BEAT * 1.6) * 0.5)
            add(low, t0 + 2.5 * BEAT, bass(root, BEAT * 1.2) * 0.4)
            for bt in (0, 2.5): add(drums, t0 + bt * BEAT, kick() * 0.75)
            for bt in (1, 3): add(drums, t0 + bt * BEAT, snare(rng) * 0.2)
            for e in range(8):
                add(drums, t0 + e * BEAT / 2 + (sw if e % 2 else 0), hat(rng) * (0.10 if e % 2 else 0.06))
        if b >= 4:
            for i, note in enumerate(MELODY[b % 8]):
                if note is not None: add(lead, t0 + i * BEAT + (sw if i % 2 else 0), bell(hz(note)) * 0.13)
    mix = reverb(keys, 0.3) + low + drums + reverb(lead, 0.45)
    # ローファイ感: 軽いローパスとサチュレーション
    mix = np.convolve(mix, np.ones(5) / 5, mode='same')
    mix = np.tanh(mix * 1.4) / 1.4
    f = int(1.2 * SR); o = int(3.0 * SR)
    mix[:f] *= np.linspace(0, 1, f); mix[-o:] *= np.linspace(1, 0, o) ** 1.5
    return (mix / np.max(np.abs(mix)) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 73.4
    out = sys.argv[2] if len(sys.argv) > 2 else 'output/bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out)
