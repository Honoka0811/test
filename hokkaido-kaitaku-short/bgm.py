# -*- coding: utf-8 -*-
"""静かで不穏なドキュメンタリー風BGMを numpy だけで合成する(外部音源不要・権利フリー)。
Aマイナー / 60BPM。低音ドローン + 倍音パッド + 風のノイズ + まばらなピアノ風の音 + 場面転換の低い打音。
単体実行: python3 bgm.py [秒数] [出力wav] [打音を入れる秒,…]
"""
import sys, wave
import numpy as np

SR = 48000
BAR = 4.0
#        Am              Am              F               F               Dm              Dm              E               E
PROG = [[45, 52, 57, 60], [45, 52, 57, 60], [41, 48, 53, 57], [41, 48, 53, 57], [38, 50, 53, 57], [38, 50, 53, 57], [40, 47, 52, 56], [40, 47, 52, 56],
        [45, 52, 57, 60], [45, 52, 57, 60], [41, 48, 53, 57], [41, 48, 53, 57], [38, 50, 53, 57], [40, 47, 52, 56], [45, 52, 57, 60], [45, 52, 57, 60]]
# ピアノ風の旋律(小節ごとの (拍, MIDIノート))。間を多く取る
MEL = [[], [(2, 76)], [(0, 72), (2.5, 69)], [(1, 77)], [(0, 74), (2, 69)], [(1.5, 77), (3, 74)], [(0, 71)], [(1, 68), (3, 71)],
       [(0, 72), (2, 76)], [(1, 81)], [(0, 77), (2.5, 72)], [(1, 69)], [(0, 74), (2, 77)], [(0, 71), (2, 68)], [(0, 69)], []]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if 0 <= s < e: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.002 * np.sin(2 * np.pi * 0.19 * t + rng.uniform(0, 6.28))
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.005, 0.005):
        for h in range(1, 6):
            sig += (1 / h ** 2.0) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + rng.uniform(0, 6.28))
    return sig

def piano(f, dur=3.2):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t / d) for h, a, d in ((1, 1, 1.1), (2, .35, .7), (3, .12, .4), (4.02, .05, .25)))
    return (sig * np.minimum(1, t / 0.006)).astype(np.float32)

def boom(rng, f0=70.0, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 36 + (f0 - 36) * np.exp(-t / 0.10)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55)
    click = rng.standard_normal(n).astype(np.float32) * np.exp(-t / 0.015)
    click = np.convolve(click, np.ones(160) / 160, mode='same')
    return (body + 0.3 * click).astype(np.float32)

def wind(n, rng):
    x = rng.standard_normal(n).astype(np.float32)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    X *= np.exp(-((np.log(np.maximum(f, 1)) - np.log(420)) ** 2) / (2 * 0.55 ** 2))   # 420Hz 付近の帯域ノイズ
    x = np.fft.irfft(X, n).astype(np.float32); t = np.arange(n) / SR
    return x / np.max(np.abs(x)) * (0.55 + 0.45 * np.sin(2 * np.pi * 0.07 * t + 1.0) * np.sin(2 * np.pi * 0.031 * t))

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.78), (1877, 0.76), (2251, 0.74), (2687, 0.72), (12007, 0.5))) / 5
    return (1 - mix) * x + mix * wet

def generate(total, hits=(), seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pad = np.zeros(n, dtype=np.float32); drone = np.zeros(n, dtype=np.float32)
    mel = np.zeros(n, dtype=np.float32); bm = np.zeros(n, dtype=np.float32)
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; chord = PROG[b % 16]; dur = BAR + 1.5
        sig = sum(pad_note(midi(m), dur, rng) * (1.0 if i < 2 else 0.6) for i, m in enumerate(chord))
        add(pad, t0, sig * env_ar(len(sig), 1.4, 1.5))
        f = midi(chord[0] - 12); tt = np.arange(int(dur * SR)) / SR
        d = (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * 2 * f * tt) + 0.2 * np.sin(2 * np.pi * 3.01 * f * tt)) * (1 + 0.2 * np.sin(2 * np.pi * 0.13 * tt))
        add(drone, t0, d.astype(np.float32) * env_ar(len(d), 1.4, 1.5))
        if t0 >= 8:   # 旋律は導入のあとから
            for beat, m in MEL[b % 16]:
                add(mel, t0 + beat, piano(midi(m)) * rng.uniform(0.7, 1.0))
    for h in hits:
        add(bm, h, boom(rng))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.5 * norm(pad) + 0.45 * norm(drone) + 0.10 * wind(n, rng) + 0.42 * reverb(norm(mel), 0.55) + (0.75 * norm(bm) if len(hits) else 0)
    mix = reverb(mix, 0.2)
    mix *= env_ar(len(mix), 1.2, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 58.64
    out = sys.argv[2] if len(sys.argv) > 2 else 'audio/bgm.wav'
    hits = [float(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 else []
    x = generate(total, hits)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
