# -*- coding: utf-8 -*-
"""不気味系BGMを numpy だけで合成する(外部音源不要・権利フリー)。
構成: うなりのある低音ドローン + 半音でぶつかる不協和パッド + オルゴール風の高音(短2度・三全音中心)
      + 時計の秒針音 + 心臓の鼓動 + シーン転換のインパクト音 + 逆再生スウェル + 簡易リバーブ
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig, gain=1.0):
    s = int(start_s * SR)
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * gain

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same').astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.35):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.78), (1877, 0.76), (2251, 0.74), (2803, 0.72), (13007, 0.5))) / 5
    return (1 - mix) * x + mix * wet

# ---------- 音源 ----------
def drone(total, rng):
    """D1 と半音上 Eb1 を薄く重ね、ゆっくりうなる低音"""
    n = int(total * SR); t = np.arange(n) / SR
    f = midi(26)  # D1
    lfo = 1 + 0.35 * np.sin(2 * np.pi * 0.07 * t)
    x = (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * (f * 1.004) * t)
         + 0.35 * np.sin(2 * np.pi * 2 * f * t + 1.0)
         + 0.18 * np.sin(2 * np.pi * midi(27) * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.031 * t)))
    # 風のようなノイズ(強いローパス)
    wind = lowpass(lowpass(rng.standard_normal(n).astype(np.float32), 400), 400)
    wind *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * t + 2))
    return (x * lfo + 6.0 * wind).astype(np.float32)

def cluster_pad(dur, notes, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for m in notes:
        f = midi(m)
        vib = 1 + 0.003 * np.sin(2 * np.pi * rng.uniform(0.1, 0.3) * t + rng.uniform(0, 6.28))
        for h, a in ((1, 1.0), (2, 0.35), (3, 0.15)):
            sig += a * np.sin(2 * np.pi * f * h * vib * t + rng.uniform(0, 6.28))
    return sig * env_ar(n, dur * 0.4, dur * 0.4)

def music_box(f, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.15)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.05))
    return (x * np.exp(-t / 0.6)).astype(np.float32)

def tick(rng, hi=True):
    n = int(0.05 * SR); t = np.arange(n) / SR
    f = 3200 if hi else 2400
    return ((np.sin(2 * np.pi * f * t) * 0.6 + rng.standard_normal(n) * 0.4) * np.exp(-t / 0.004)).astype(np.float32)

def heartbeat(rng):
    def thump(f0, d):
        n = int(d * SR); t = np.arange(n) / SR
        f = 35 + (f0 - 35) * np.exp(-t / 0.05)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)).astype(np.float32)
    x = np.zeros(int(0.8 * SR), dtype=np.float32)
    add(x, 0, thump(70, 0.4)); add(x, 0.22, thump(60, 0.4), 0.7)
    return x

def impact(rng, dur=3.5):
    """低い衝撃音 + 金属的な残響"""
    n = int(dur * SR); t = np.arange(n) / SR
    f = 30 + 90 * np.exp(-t / 0.12)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    noise = lowpass(rng.standard_normal(n).astype(np.float32), 30) * np.exp(-t / 0.25)
    metal = sum(np.sin(2 * np.pi * fr * t) / (i + 1) for i, fr in enumerate((331, 467, 709, 1013))) * np.exp(-t / 1.2) * 0.25
    return (boom + 1.5 * noise + metal).astype(np.float32)

def reverse_swell(rng, dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    x = lowpass(rng.standard_normal(n).astype(np.float32), 12) * np.exp(-t / 0.5)
    x += 0.4 * sum(np.sin(2 * np.pi * midi(m) * t) for m in (62, 63, 68)) * np.exp(-t / 0.6)
    return x[::-1].astype(np.float32).copy()

# 不協和パッド(D・Eb・Ab ... 短2度と三全音)
PADS = [[50, 51, 56], [49, 50, 55], [50, 53, 56], [47, 50, 51]]
# オルゴールの旋律(D短調の崩れた子守歌風)
BOX = [74, 75, 81, 74, 77, 73, 74, None, 81, 80, 74, 75, 70, None, 69, None]

def generate(total, hits=(), heart=(), seed=13):
    """hits: インパクト音を鳴らす秒の一覧 / heart: (開始秒, 終了秒) 心音を鳴らす区間"""
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    dr = drone(total, rng)
    pad = np.zeros(n, dtype=np.float32); box = np.zeros(n, dtype=np.float32)
    clk = np.zeros(n, dtype=np.float32); fx = np.zeros(n, dtype=np.float32)
    # パッド: 8 秒ごとに重ねる
    for i, t0 in enumerate(np.arange(0, total, 8.0)):
        add(pad, t0 - 1.5, cluster_pad(11.0, PADS[i % len(PADS)], rng))
    # オルゴール: 0.75 秒間隔、ときどき音程が狂う
    for i, t0 in enumerate(np.arange(0.5, total - 2, 0.75)):
        m = BOX[i % len(BOX)]
        if m is None: continue
        detune = 1 + rng.normal(0, 0.006)
        add(box, t0 + rng.normal(0, 0.015), music_box(midi(m) * detune), rng.uniform(0.6, 1.0))
    # 時計: 1 秒ごと(チク・タク)
    for i, t0 in enumerate(np.arange(0, total, 1.0)):
        add(clk, t0, tick(rng, hi=(i % 2 == 0)), 0.9)
    # 心音
    for a, b in heart:
        for t0 in np.arange(a, b, 0.85):
            add(fx, t0, heartbeat(rng), 0.9)
    # インパクト + 直前の逆再生スウェル
    for h in hits:
        add(fx, h - 1.6, reverse_swell(rng), 0.35)
        add(fx, h, impact(rng), 1.0)

    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.55 * norm(dr) + 0.32 * norm(pad) + 0.20 * reverb(norm(box), 0.6)
           + 0.10 * norm(clk) + 0.75 * norm(fx))
    mix = reverb(mix, 0.2)
    mix *= env_ar(len(mix), 1.5, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 68.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total, hits=(0.3, 31.5, 59.0), heart=((22.5, 31.0),))
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
