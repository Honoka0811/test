# -*- coding: utf-8 -*-
"""バッハ「平均律クラヴィーア曲集 第1巻 第1番 プレリュード ハ長調(BWV 846)」のアレンジを numpy だけで合成する BGM。
原曲はパブリックドメイン、音源も自作のため権利表記は不要。
構成: 原曲どおりの分散和音(ハープ/ピアノ風の柔らかい撥弦音) + 各小節の和音を薄く支える弦パッド + 低音 + 軽いリバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 64
BEAT = 60.0 / BPM           # 四分音符
BAR = 4 * BEAT              # 1 小節(16 個の十六分音符)
SIXT = BEAT / 4

N = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def m(name):
    p = N[name[0]]; i = 1
    if name[1] == '#': p += 1; i = 2
    elif name[1] == 'b': p -= 1; i = 2
    return 12 * (int(name[i:]) + 1) + p
def hz(n): return 440.0 * 2 ** ((n - 69) / 12)

# 各小節の 5 音(原曲の 1〜19 小節 → ハ長調に戻ったところで終止)。
# 原曲は n1 n2 n3 n4 n5 n3 n4 n5 を 1 小節に 2 回繰り返す
BARS = [
    'C4 E4 G4 C5 E5', 'C4 D4 A4 D5 F5', 'B3 D4 G4 D5 F5', 'C4 E4 G4 C5 E5',
    'C4 E4 A4 E5 A5', 'C4 D4 F#4 A4 D5', 'B3 D4 G4 D5 G5', 'B3 C4 E4 G4 C5',
    'A3 C4 E4 G4 C5', 'D3 A3 D4 F#4 C5', 'G3 B3 D4 G4 B4', 'G3 Bb3 E4 G4 C#5',
    'F3 A3 D4 A4 D5', 'F3 Ab3 D4 F4 B4', 'E3 G3 C4 G4 C5', 'E3 F3 A3 C4 F4',
    'D3 F3 A3 C4 F4', 'G2 D3 G3 B3 F4', 'C3 E3 G3 C4 E4',
]
FINAL = 'C3 E3 G3 C4 E4 G4 C5'   # 終止の和音

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: env[:na] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, na))        # 滑らかな立ち上がり
    if nr: env[n - nr:] = np.minimum(env[n - nr:], 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nr)))
    return env

def pluck(f, dur=1.6, vel=1.0):
    """ハープ/ピアノ風の撥弦音。少数の倍音を速く減衰させ、基音を残す。アタックは 4ms のコサインで無音から立ち上げる"""
    n = int(dur * SR); t = np.arange(n) / SR
    body = np.clip(500 / f, 0.35, 1.0)      # 高音ほど倍音控えめ
    sig = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9)
           + 0.45 * body * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.35)
           + 0.20 * body * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.18)
           + 0.08 * body * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.10))
    return (sig * env_ar(n, 0.004, 0.3) * vel * 0.45).astype(np.float32)

def pad(f, dur, rng):
    """弦パッド: 倍音少なめ・ゆっくり立ち上がる"""
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.002 * np.sin(2 * np.pi * 5.2 * t + rng.uniform(0, 6.28))
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.0025, 0.0025):
        for h, a in ((1, 1.0), (2, 0.35), (3, 0.15)):
            sig += a * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + rng.uniform(0, 6.28))
    return (sig * env_ar(n, 0.6, 0.8) * 0.2).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return (sig * env_ar(n, 0.02, 0.6) * np.exp(-t / 2.5) * 0.5).astype(np.float32)

def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same').astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.16):
    """ホール風の軽い残響: 長めの遅延・低めのフィードバック、ウェット成分は高域を落とす"""
    wet = sum(comb(x, d, g) for d, g in ((2213, 0.52), (2719, 0.50), (3307, 0.48), (3907, 0.46))) / 4
    wet = lowpass(wet, 40)
    return (1 - mix) * x + mix * wet

def generate(total, seed=5):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    arp = np.zeros(n, dtype=np.float32); strings = np.zeros(n, dtype=np.float32); low = np.zeros(n, dtype=np.float32)
    nb = len(BARS)
    for b in range(nb):
        t0 = b * BAR
        notes = BARS[b].split()
        n1, n2, n3, n4, n5 = notes
        seq = [n1, n2, n3, n4, n5, n3, n4, n5] * 2
        for k, name in enumerate(seq):
            vel = 1.0 if k % 8 == 0 else (0.85 if k % 4 == 0 else 0.7)
            add(arp, t0 + k * SIXT, pluck(hz(m(name)), vel=vel))
        for i, name in enumerate(notes):
            add(strings, t0, pad(hz(m(name)), BAR + 0.8, rng) * (1.0 if i < 2 else 0.6))
        add(low, t0, bass(hz(m(n1) - 12), BAR))
    # 終止の和音(残り時間に向けて、ゆっくりアルペジオ → 保持)
    t0 = nb * BAR
    for i, name in enumerate(FINAL.split()):
        add(arp, t0 + i * SIXT * 1.5, pluck(hz(m(name)), dur=5.0, vel=0.9))
        add(strings, t0, pad(hz(m(name)), max(1.0, total - t0), rng) * 0.9)
    add(low, t0, bass(hz(m('C2')), max(1.0, total - t0)))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.80 * norm(arp) + 0.28 * norm(strings) + 0.30 * norm(low)
    mix = reverb(mix, 0.16)
    mix *= env_ar(len(mix), 1.5, 3.5)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 77.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
