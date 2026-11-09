# -*- coding: utf-8 -*-
"""不気味なBGMをプログラムで合成する(外部音源不要・権利フリー)。
構成: 短2度でうなる低音ドローン / 音程が揺れる壊れたオルゴール / 心音 / 風のようなノイズ /
シーン切替の低い衝撃音(リバース・スウェル付き) / 簡易リバーブ
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR)
    if s < 0: sig, s = sig[-s:], 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def lowpass(x, a):
    """1次ローパス(a: 0-1、小さいほど暗い)をブロック単位で近似せず素直に計算"""
    from scipy.signal import lfilter
    return lfilter([a], [1, a - 1], x).astype(np.float32)

def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y

def reverb(x, mix=0.35):
    wet = sum(comb(x, d, g) for d, g in ((1931, 0.80), (2357, 0.78), (2791, 0.76), (3307, 0.74), (14009, 0.5))) / 5
    wet = lowpass(wet, 0.25)
    return (1 - mix) * x + mix * wet

def drone(n, rng):
    t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for f, a in ((55.0, 1.0), (58.27, 0.55), (110.0, 0.35), (155.56, 0.18)):   # A1 / Bb1(短2度) / A2 / Eb3(三全音)
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(0.03, 0.07) * t + rng.uniform(0, 6.28))
        x += a * lfo * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t + 1))
    return x * 0.16

def wind(n, rng):
    t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    x = lowpass(noise, 0.02) * 4
    x = x - lowpass(x, 0.002)                       # 低域を少し削ってこもった風音に
    amp = 0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t) * np.sin(2 * np.pi * 0.037 * t + 1)
    return x * amp * 0.25

def music_box_note(f, dur, rng, warble):
    n = int(dur * SR); t = np.arange(n) / SR
    fm = f * (1 + warble)                           # テープのような音程の揺れ
    sig = np.zeros(n, dtype=np.float32)
    for ratio, a, dec in ((1.0, 1.0, 1.2), (2.76, 0.35, 0.4), (5.40, 0.18, 0.18), (8.93, 0.08, 0.08)):  # ベルの非整数倍音
        sig += a * np.sin(2 * np.pi * fm * ratio * t + rng.uniform(0, 6.28)) * np.exp(-t / dec)
    att = min(n, 80); sig[:att] *= np.linspace(0, 1, att)
    return sig

def heartbeat():
    def thump(f0, dur, amp):
        n = int(dur * SR); t = np.arange(n) / SR
        f = 35 + (f0 - 35) * np.exp(-t / 0.05)
        return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.09)
    a = thump(70, 0.4, 1.0); b = thump(60, 0.4, 0.7)
    out = np.zeros(int(0.65 * SR), dtype=np.float32)
    out[:len(a)] += a; out[int(0.24 * SR):int(0.24 * SR) + len(b)] += b
    return out

def boom(rng):
    """シーン切替の衝撃音: 直前にリバースのスウェル、着地で低い打撃+金属的な残響"""
    n = int(3.0 * SR); t = np.arange(n) / SR
    f = 30 + 60 * np.exp(-t / 0.15)
    hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    metal = sum(np.sin(2 * np.pi * fr * t + rng.uniform(0, 6)) for fr in (311.1, 467.3, 739.9, 1103.0)) * np.exp(-t / 1.4) * 0.06
    nz = lowpass(rng.standard_normal(n).astype(np.float32), 0.05) * np.exp(-t / 0.25) * 0.8
    swell_n = int(1.2 * SR); ts = np.arange(swell_n) / SR
    swell = lowpass(rng.standard_normal(swell_n).astype(np.float32), 0.08) * (ts / ts[-1]) ** 3 * 1.2
    return swell, (hit + metal + nz).astype(np.float32)

def generate(total, hits=(), seed=21):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    t = np.arange(n) / SR
    out = drone(n, rng) + wind(n, rng)

    # 壊れたオルゴール: Aマイナー + 三全音。2.4秒周期でぽつぽつ鳴らす
    melody = [81, 84, 83, 75, 81, 77, 76, 75,   81, 84, 88, 87, 86, 84, 83, 80]
    box = np.zeros(n, dtype=np.float32)
    step = 0.6; i = 0; s = 2.0
    while s < total - 3:
        note = melody[i % len(melody)]
        if not (i % 8 == 7 and rng.random() < 0.5):            # ときどき音が抜ける
            dur = 2.5
            tt = np.arange(int(dur * SR)) / SR
            warble = 0.012 * np.sin(2 * np.pi * 0.7 * (tt + s)) + 0.0025 * np.sin(2 * np.pi * 5.1 * tt)
            add(box, s + rng.uniform(-0.03, 0.05), music_box_note(midi(note), dur, rng, warble) * rng.uniform(0.7, 1.0))
        s += step * (1.6 if i % 4 == 3 else 1.0)                 # 4音ごとに間を置く
        i += 1
    box = box * (0.5 + 0.5 * np.clip((t - 1.5) / 4, 0, 1))      # 冒頭はフェードイン
    out += box * 0.16

    # 心音: 中盤から入り、終盤にかけて少しずつ強く
    hb = heartbeat(); period = 1.25; s = 20.0
    while s < total - 4:
        add(out, s, hb * 0.45 * min(1.0, 0.4 + (s - 20) / 60))
        s += period

    for h in hits:
        swell, hit = boom(rng)
        add(out, h - len(swell) / SR, swell * 0.10)
        add(out, h, hit * 0.55)

    out = reverb(out)
    fade = int(2.5 * SR); out[-fade:] *= np.linspace(1, 0, fade) ** 2
    out[:int(0.8 * SR)] *= np.linspace(0, 1, int(0.8 * SR))
    return (out / np.max(np.abs(out)) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    path = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', path)
