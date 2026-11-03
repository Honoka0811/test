# -*- coding: utf-8 -*-
"""パッヘルベル「カノン(ニ長調)」のオリジナルアレンジを numpy だけで合成する BGM。
原曲は著作権切れ(パブリックドメイン)。音源も自作なので権利表記は不要。
構成: 通奏低音(チェロ風) + 弦パッド + ピアノ/ハープ風の主旋律 + ピチカートの分散和音 + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 104
BEAT = 60.0 / BPM           # 四分音符
CYCLE = 16 * BEAT           # 8 和音 × 2 拍 = 4 小節 ≒ 9.2 秒

# ニ長調の音名 → MIDI
N = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def m(name):
    """'F#5' のような表記を MIDI ノート番号へ"""
    p = N[name[0]]; i = 1
    if name[1] == '#': p += 1; i = 2
    elif name[1] == 'b': p -= 1; i = 2
    return 12 * (int(name[i:]) + 1) + p

def hz(n): return 440.0 * 2 ** ((n - 69) / 12)

# 通奏低音(各 2 拍)と和音: D A Bm F#m G D G A
BASS = ['D3', 'A2', 'B2', 'F#2', 'G2', 'D2', 'G2', 'A2']
CHORDS = [['D4', 'F#4', 'A4'], ['A3', 'C#4', 'E4'], ['B3', 'D4', 'F#4'], ['F#3', 'A3', 'C#4'],
          ['G3', 'B3', 'D4'], ['D4', 'F#4', 'A4'], ['G3', 'B3', 'D4'], ['A3', 'C#4', 'E4']]

# 旋律のバリエーション。各要素は (音名, 長さ[拍])。1 サイクル = 16 拍
def half(notes): return [(n, 2.0) for n in notes]
def quarter(notes): return [(n, 1.0) for n in notes]
def eighth(notes): return [(n, 0.5) for n in notes]
def sixteenth(notes): return [(n, 0.25) for n in notes]

VAR_HALF_1 = half('F#5 E5 D5 C#5 B4 A4 B4 C#5'.split())
VAR_HALF_2 = half('D5 C#5 B4 A4 G4 F#4 G4 E4'.split())
VAR_QUARTER = quarter('F#5 D5 E5 C#5 D5 B4 C#5 A4 B4 G4 A4 F#4 G4 B4 A4 C#5'.split())
VAR_EIGHTH_1 = eighth('D5 C#5 D5 D4 C#4 A4 E4 F#4  D4 D5 C#5 B4 C#5 F#5 A5 B5  '
                      'G5 F#5 E5 G5 F#5 E5 D5 C#5  B4 A4 G4 F#4 E4 G4 F#4 E4'.split())
VAR_EIGHTH_2 = eighth('D4 E4 F#4 G4 A4 E4 A4 G4  F#4 B4 A4 G4 A4 G4 F#4 E4  '
                      'D4 B3 B4 C#5 D5 C#5 B4 A4  G4 F#4 E4 B4 A4 B4 A4 G4'.split())
VAR_SIXTEENTH = ([('F#5', 0.5)] + sixteenth('A5 F#5 G5 A5 F#5 G5'.split())
                 + sixteenth('A4 B4 C#5 D5 E5 F#5 G5 A5'.split())
                 + sixteenth('F#5 D5 E5 F#5 F#4 G4 A4 B4'.split())
                 + sixteenth('A4 G4 A4 F#4 G4 A4 G4 F#4'.split())
                 + sixteenth('G4 B4 A4 G4 F#4 E4 F#4 E4'.split())
                 + sixteenth('D4 E4 F#4 G4 A4 B4 A4 F#4'.split())
                 + sixteenth('G4 B4 A4 B4 C#5 D5 C#5 B4'.split())
                 + sixteenth('A4 B4 C#5 D5 E5 F#5 G5 A5'.split()))
VAR_HALF_HIGH = half('F#5 E5 D5 C#5 B4 A4 B4 C#5'.split())

# サイクルごとの構成: (旋律, ピチカート有無, ハープの重ね有無)
PLAN = [
    (None,            False, False),   # 0: 低音 + パッド(導入)
    (VAR_HALF_1,      False, False),   # 1
    (VAR_HALF_2,      True,  False),   # 2
    (VAR_QUARTER,     True,  False),   # 3
    (VAR_EIGHTH_1,    True,  True),    # 4
    (VAR_EIGHTH_2,    True,  True),    # 5
    (VAR_SIXTEENTH,   True,  True),    # 6
    (VAR_HALF_HIGH,   True,  True),    # 7
    (VAR_EIGHTH_1,    True,  True),    # 8(余り)
]

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: env[:na] = np.linspace(0, 1, na)
    if nr: env[n - nr:] = np.minimum(env[n - nr:], np.linspace(1, 0, nr))
    return env

def piano(f, dur, vel=1.0):
    """ピアノ/ハープ風: 倍音の減衰をずらした加算合成 + ごく短いアタックノイズ"""
    n = int((dur + 1.2) * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    bright = np.clip(600 / f, 0.4, 1.4)                   # 低音ほど倍音豊か
    for h in range(1, 7):
        amp = (1 / h ** 1.1) * (bright if h > 1 else 1.0)
        decay = 0.9 / (1 + 0.45 * (h - 1)) * np.clip(800 / f, 0.5, 1.8)
        sig += amp * np.sin(2 * np.pi * f * h * t * (1 + 0.0004 * h)) * np.exp(-t / decay)
    # 音の終わりをなだらかに(次の音とのつながり)
    sig *= env_ar(n, 0.003, 0.25)
    atk = np.random.default_rng(int(f)).standard_normal(int(0.004 * SR)).astype(np.float32)
    atk = np.convolve(atk, np.ones(20) / 20, mode='same') * 0.25   # 高域を落として柔らかい打鍵音に
    sig[:len(atk)] += atk * np.linspace(1, 0, len(atk))
    return (sig * vel * 0.5).astype(np.float32)

def harp(f, dur, vel=1.0):
    n = int((dur + 0.8) * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.6) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.3) \
        + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.2)
    return (sig * env_ar(n, 0.002, 0.2) * vel * 0.4).astype(np.float32)

def pizz(f, vel=1.0):
    n = int(0.45 * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t)) * np.exp(-t / 0.09)
    return (sig * vel * 0.5).astype(np.float32)

def cello(f, dur, rng):
    n = int((dur + 0.4) * SR); t = np.arange(n) / SR
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5.0 * t + rng.uniform(0, 6.28))
    sig = sum((1 / h ** 1.3) * np.sin(2 * np.pi * f * h * vib * t) for h in range(1, 6))
    return (sig * env_ar(n, 0.08, 0.4) * 0.5).astype(np.float32)

def strings(f, dur, rng):
    n = int((dur + 0.6) * SR); t = np.arange(n) / SR
    vib = 1 + 0.0025 * np.sin(2 * np.pi * 5.5 * t + rng.uniform(0, 6.28))
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.003, 0.0, 0.003):
        for h in range(1, 8):
            sig += (1 / h ** 1.5) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + rng.uniform(0, 6.28))
    return (sig * env_ar(n, 0.35, 0.6) * 0.33).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1361, 0.70), (1693, 0.68), (2053, 0.66), (2399, 0.64))) / 4
    # ウェット成分の高域を少し落とす
    wet = np.convolve(wet, np.ones(24) / 24, mode='same')
    return (1 - mix) * x + mix * wet

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    bass = np.zeros(n, dtype=np.float32); pad = np.zeros(n, dtype=np.float32)
    mel = np.zeros(n, dtype=np.float32); plk = np.zeros(n, dtype=np.float32)
    ncyc = int(np.ceil(total / CYCLE))
    for c in range(ncyc):
        t0 = c * CYCLE
        melody, use_pizz, use_harp = PLAN[min(c, len(PLAN) - 1)]
        for k in range(8):
            ts = t0 + k * 2 * BEAT
            add(bass, ts, cello(hz(m(BASS[k])), 2 * BEAT, rng))
            for i, note in enumerate(CHORDS[k]):
                add(pad, ts, strings(hz(m(note)), 2 * BEAT, rng) * (0.8 if i else 1.0))
            if use_pizz:
                # 分散和音: 根音-5度-3度-5度 を八分音符で
                seq = [CHORDS[k][0], CHORDS[k][2], CHORDS[k][1], CHORDS[k][2]]
                for j, note in enumerate(seq):
                    add(plk, ts + j * BEAT / 2, pizz(hz(m(note) - 12), 0.9 if j == 0 else 0.6))
        if melody:
            t = t0
            for name, beats in melody:
                dur = beats * BEAT
                f = hz(m(name))
                vel = 1.0 if beats >= 1 else 0.85
                add(mel, t, piano(f, dur, vel))
                if use_harp:
                    add(mel, t, harp(f * 2, dur, 0.35))
                t += dur
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.42 * norm(bass) + 0.40 * norm(pad) + 0.85 * norm(mel) + 0.30 * norm(plk)
    mix = reverb(mix, 0.22)
    mix *= env_ar(len(mix), 1.5, 3.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 70.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
