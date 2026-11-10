# -*- coding: utf-8 -*-
"""「機械の時代」風BGMをプログラムで合成する(外部音源不要・権利フリー)。
Aマイナー→Cメジャー / 96BPM。
弦楽ピチカート風の8分音符オスティナート + 柔らかいパッド + 低音ベース +
時計・歯車のような金属的なチクタク音 + 蒸気機関のピストンを思わせるキック + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 96
BEAT = 60.0 / BPM
BAR = BEAT * 4

# コード進行(MIDIノート)。8小節でループ: Am F C G / Am F G E
PROG = [
    [57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62],
    [57, 60, 64], [53, 57, 60], [55, 59, 62], [52, 56, 59],
]
ROOTS = [45, 41, 48, 43, 45, 41, 43, 40]
# 8分音符オスティナートの音型(コード構成音のインデックス, 12 = 1オクターブ上)
PATTERN = [0, 1, 2, 1, 12, 1, 2, 1]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def pizz(f, dur=0.45):
    """ピチカート風: 倍音を含む減衰音"""
    n = int(dur * SR); t = np.arange(n) / SR
    sig = sum((0.6 ** h) * np.sin(2 * np.pi * f * (h + 1) * t) for h in range(5))
    return (sig * np.exp(-t / 0.12) * env_ar(n, 0.003, 0.05)).astype(np.float32)

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.005, 0.005):
        for h in range(1, 6):
            sig += (1 / h ** 2) * np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6.28))
    return sig

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return (sig * np.exp(-t / 0.5) * env_ar(n, 0.01, 0.08)).astype(np.float32)

def tick(rng, bright=1.0, dur=0.05):
    """時計・歯車のような短い金属音"""
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    hp = noise - np.convolve(noise, np.ones(8) / 8, mode='same')  # 簡易ハイパス
    ring = np.sin(2 * np.pi * 3200 * bright * t) * 0.5
    return ((hp * 0.6 + ring) * np.exp(-t / 0.012)).astype(np.float32)

def kick(dur=0.35):
    """ピストンのような低いキック"""
    n = int(dur * SR); t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)).astype(np.float32)

def steam(rng, dur=0.25):
    """蒸気の「シュッ」"""
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    hp = noise - np.convolve(noise, np.ones(4) / 4, mode='same')
    return (hp * np.exp(-t / 0.07) * env_ar(n, 0.01, 0.05)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (9001, 0.4))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pad = np.zeros(n, np.float32); ost = np.zeros(n, np.float32); bs = np.zeros(n, np.float32)
    perc = np.zeros(n, np.float32); kk = np.zeros(n, np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; chord = PROG[b % 8]; root = ROOTS[b % 8]
        # パッド
        dur = BAR + 0.8
        sig = sum(pad_note(midi(m), dur, rng) for m in chord)
        add(pad, t0, sig * env_ar(len(sig), 0.6, 0.8))
        # 低音: 1拍目と3拍目
        add(bs, t0, bass(midi(root - 12), BEAT * 1.8))
        add(bs, t0 + 2 * BEAT, bass(midi(root - 12), BEAT * 1.8) * 0.8)
        # オスティナート(4小節目以降)
        if t0 >= BAR * 2 - 0.01:
            for k, idx in enumerate(PATTERN):
                m = chord[idx] + 12 if idx < 12 else chord[0] + 24
                add(ost, t0 + k * BEAT / 2, pizz(midi(m)) * (1.0 if k % 2 == 0 else 0.7))
        # チクタク(16分音符、表拍を強く)。最初から鳴らす
        for k in range(16):
            amp = 0.9 if k % 4 == 0 else (0.5 if k % 2 == 0 else 0.25)
            add(perc, t0 + k * BEAT / 4, tick(rng, 1.0 if k % 2 == 0 else 1.35) * amp)
        # ピストンキック + 蒸気(16秒以降、強さは徐々に上がる)
        inten = min(1.0, max(0.0, (t0 - 12) / 16))
        if inten > 0:
            for k in range(4):
                add(kk, t0 + k * BEAT, kick() * inten * (1.0 if k % 2 == 0 else 0.6))
            add(perc, t0 + 1.5 * BEAT, steam(rng) * 0.5 * inten)
            add(perc, t0 + 3.5 * BEAT, steam(rng) * 0.5 * inten)
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.38 * norm(pad) + 0.5 * reverb(norm(ost), 0.35) + 0.5 * norm(bs)
           + 0.22 * norm(perc) + 0.55 * norm(kk))
    mix = reverb(mix, 0.12)
    mix *= env_ar(len(mix), 1.5, 3.5)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 67.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
