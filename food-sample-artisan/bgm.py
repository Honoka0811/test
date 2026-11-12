# -*- coding: utf-8 -*-
"""明るく軽快なBGMをプログラムで合成する(外部音源不要・権利フリー)。
Fメジャー / 112BPM。マリンバ風の刻み + グロッケン風メロディ + 丸いベース + シェイカー + 手拍子。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 112
BEAT = 60.0 / BPM
BAR = BEAT * 4

# コード進行(MIDIノート)。4小節ループ: F - Dm - Bb - C
PROG = [[65, 69, 72], [62, 65, 69], [58, 62, 65], [60, 64, 67]]
ROOTS = [41, 38, 46, 48]
# メロディ(8分音符単位, None=休符)。8小節分
MEL = [
    [77, None, 76, 77, 79, None, 77, None], [74, None, None, 72, 74, 77, None, None],
    [74, None, 72, 70, 72, None, 74, None], [72, None, None, None, 67, None, 69, 70],
    [77, None, 76, 77, 81, None, 79, None], [77, None, 74, None, 72, 74, None, None],
    [70, 72, 74, None, 77, None, 74, None], [72, None, None, None, None, None, None, None],
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def marimba(f, dur=0.5):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.18) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.03)
    s[:96] *= np.linspace(0, 1, 96)
    return s.astype(np.float32)

def glock(f, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.08)) * np.exp(-t / 0.35)
    s[:48] *= np.linspace(0, 1, 48)
    return s.astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(1, t / 0.01) * np.exp(-t / 0.5)
    return (s * env).astype(np.float32)

def noise_hit(rng, dur, decay, smooth):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(smooth) / smooth, mode='same')  # 低域を削って高域寄りに
    return (x * np.exp(-t / decay)).astype(np.float32)

def kick(dur=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def echo(x, delay_s=BEAT * 0.75, g=0.3, n=3):
    y = x.copy(); d = int(delay_s * SR)
    for k in range(1, n + 1):
        y[d * k:] += (g ** k) * x[:len(x) - d * k]
    return y

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    mar = np.zeros(n, np.float32); mel = np.zeros(n, np.float32); bas = np.zeros(n, np.float32)
    perc = np.zeros(n, np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; chord = PROG[b % 4]
        # マリンバ: 8分でアルペジオ
        pat = [0, 1, 2, 1, 0, 2, 1, 2]
        for k in range(8):
            m = chord[pat[k]] + (12 if k in (2, 5) else 0)
            add(mar, t0 + k * BEAT / 2, marimba(midi(m)) * (1.0 if k % 2 == 0 else 0.7))
        # ベース: 1拍目と3拍目、3拍目裏に5度
        r = ROOTS[b % 4]
        add(bas, t0, bass(midi(r), BEAT * 1.5))
        add(bas, t0 + 2 * BEAT, bass(midi(r), BEAT))
        add(bas, t0 + 3.5 * BEAT, bass(midi(r + 7), BEAT * 0.5) * 0.7)
        # メロディ: 4小節目以降(イントロ後)
        if b >= 2:
            for k, m in enumerate(MEL[(b - 2) % 8]):
                if m is not None:
                    add(mel, t0 + k * BEAT / 2, glock(midi(m)))
        # パーカッション: 2小節目から
        if b >= 1:
            for k in range(8):
                add(perc, t0 + k * BEAT / 2, noise_hit(rng, 0.08, 0.02, 8) * (0.35 if k % 2 else 0.2))
            add(perc, t0, kick() * 1.2); add(perc, t0 + 2 * BEAT, kick() * 1.0)
            for k in (1, 3):
                add(perc, t0 + k * BEAT, noise_hit(rng, 0.25, 0.06, 40) * 0.8)
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * norm(mar) + 0.5 * norm(echo(mel)) + 0.6 * norm(bas) + 0.35 * norm(perc)
    mix *= env_ar(len(mix), 0.8, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 69
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
