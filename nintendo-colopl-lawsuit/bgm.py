# -*- coding: utf-8 -*-
"""解説動画向けの軽いBGMをプログラムで合成する(外部音源不要・権利フリー)。
Cメジャー(王道進行 F△7 → G6 → Em7 → Am7)/ 92BPM。エレピ風コード + ベース + 軽いドラム + パッド + まばらなペンタトニックの装飾音。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 92
BEAT = 60.0 / BPM
BAR = BEAT * 4

PROG = [  # MIDI ノート(4 小節でループ)
    [53, 57, 60, 64],  # F△7
    [55, 59, 62, 64],  # G6
    [52, 55, 59, 62],  # Em7
    [57, 60, 64, 67],  # Am7
]
ROOTS = [41, 43, 40, 45]
PENTA = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81]  # C ペンタトニック

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def epiano(f, dur=1.4, vel=1.0):
    """エレピ風: 基音 + 弱い倍音、減衰は倍音ほど速い"""
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9)
    sig += 0.35 * np.sin(2 * np.pi * 2 * f * t + 0.3) * np.exp(-t / 0.35)
    sig += 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.18)
    sig += 0.05 * np.sin(2 * np.pi * 5.01 * f * t) * np.exp(-t / 0.08)
    att = np.minimum(1, t / 0.006)
    return (sig * att * vel).astype(np.float32)

def bass(f, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.5)
    return (sig * np.minimum(1, t / 0.01) * env_ar(n, 0.005, 0.08)).astype(np.float32)

def kick(rng):
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 42 + 90 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def snare(rng):
    n = int(0.22 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    noise = noise - np.convolve(noise, np.ones(24) / 24, mode='same')  # 低域を抜く
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    return ((0.6 * noise * np.exp(-t / 0.06)) + 0.5 * body).astype(np.float32)

def hat(rng, dur=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    noise = noise - np.convolve(noise, np.ones(8) / 8, mode='same')
    return (noise * np.exp(-t / (dur / 3))).astype(np.float32)

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.003, 0.003):
        for h in (1, 2, 3):
            sig += (1 / h ** 1.5) * np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6.28))
    return sig

def pluck(f, dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t)) * np.exp(-t / 0.3)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1361, 0.68), (1693, 0.66), (2053, 0.64), (9001, 0.35))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    keys = np.zeros(n, dtype=np.float32); bs = np.zeros(n, dtype=np.float32)
    drums = np.zeros(n, dtype=np.float32); pad = np.zeros(n, dtype=np.float32); lead = np.zeros(n, dtype=np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; chord = PROG[b % 4]; root = ROOTS[b % 4]
        # エレピ: 1 拍目(全音)、2.5 拍目(軽く)、4 拍目(軽く)
        for beat, vel in ((0, 1.0), (1.5, 0.55), (3, 0.6)):
            for i, m in enumerate(chord):
                add(keys, t0 + beat * BEAT + i * 0.012, epiano(midi(m), 1.3 if beat == 0 else 0.8, vel * (0.9 if i else 0.7)))
        # ベース: 1 拍目と 3 拍目、3.5 拍目に経過音
        add(bs, t0, bass(midi(root), 1.2)); add(bs, t0 + 2 * BEAT, bass(midi(root), 0.9))
        if b % 2 == 1: add(bs, t0 + 3.5 * BEAT, bass(midi(root + 7), 0.4) * 0.7)
        # パッド(小節をまたいでクロスフェード)
        dur = BAR + 0.8
        sig = sum(pad_note(midi(m), dur, rng) for m in chord)
        add(pad, t0, sig * env_ar(len(sig), 0.8, 0.8))
        # ドラム(イントロ 1 小節はなし)
        if b >= 1:
            add(drums, t0, kick(rng)); add(drums, t0 + 2 * BEAT, kick(rng) * 0.9)
            if b % 2 == 1: add(drums, t0 + 2.5 * BEAT, kick(rng) * 0.5)
            add(drums, t0 + BEAT, snare(rng) * 0.8); add(drums, t0 + 3 * BEAT, snare(rng) * 0.85)
            for k in range(8):
                v = 0.5 if k % 2 == 0 else 0.3
                add(drums, t0 + k * BEAT / 2, hat(rng) * v * rng.uniform(0.8, 1.0))
        # 装飾音: ペンタトニックを 2 小節に 1 回程度、まばらに
        if b >= 2 and rng.random() < 0.6:
            for k in range(8):
                if rng.random() < 0.3:
                    add(lead, t0 + k * BEAT / 2, pluck(midi(PENTA[rng.integers(0, len(PENTA))])) * rng.uniform(0.3, 0.6))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * norm(keys) + 0.45 * norm(bs) + 0.5 * norm(drums) + 0.22 * norm(pad) + 0.25 * reverb(norm(lead), 0.5)
    mix = reverb(mix, 0.12)
    mix *= env_ar(len(mix), 1.5, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
