# -*- coding: utf-8 -*-
"""BGM: パッヘルベル「カノン(ニ長調)」のポップ・アレンジを numpy だけで合成する。
原曲は著作権切れ(パブリックドメイン)、この編曲・演奏データは本リポジトリで作成したもの。
104BPM / ニ長調。ピアノ(主旋律)+ ストリングス(カノン的に追いかける第2声)+ ベース + ドラム(キック/クラップ/ハイハット)+ 簡易ステレオリバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 104
BEAT = 60.0 / BPM
CHORD = 2 * BEAT              # 1コード = 2拍(原曲の2分音符)
CYCLE = 8 * CHORD             # 8コードで1周

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
N = {}
for i, nm in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']):
    for o in range(2, 7): N[f'{nm}{o}'] = 12 * (o + 1) + i

# 原曲の低音主題(グラウンド・バス): D A B F# G D G A
BASS = ['D3', 'A2', 'B2', 'F#2', 'G2', 'D2', 'G2', 'A2']
CHORDS = [['D4', 'F#4', 'A4'], ['A3', 'C#4', 'E4'], ['B3', 'D4', 'F#4'], ['F#3', 'A3', 'C#4'],
          ['G3', 'B3', 'D4'], ['D4', 'F#4', 'A4'], ['G3', 'B3', 'D4'], ['A3', 'C#4', 'E4']]

# 変奏(各コードごとの音列。要素数で等分割)
V0 = [['F#5'], ['E5'], ['D5'], ['C#5'], ['B4'], ['A4'], ['B4'], ['C#5']]
V1 = [['D5'], ['C#5'], ['B4'], ['A4'], ['G4'], ['F#4'], ['G4'], ['E4']]
V2 = [['D5', 'F#5'], ['A5', 'G5'], ['F#5', 'D5'], ['F#5', 'E5'], ['D5', 'B4'], ['D5', 'A5'], ['G5', 'B5'], ['A5', 'G5']]
V3 = [['F#5', 'D5'], ['E5', 'C#5'], ['D5', 'B4'], ['C#5', 'A4'], ['B4', 'G4'], ['A4', 'F#4'], ['B4', 'G4'], ['C#5', 'E5']]
V4 = [['A5', 'F#5', 'D5', 'F#5'], ['E5', 'C#5', 'A4', 'C#5'], ['F#5', 'D5', 'B4', 'D5'], ['C#5', 'A4', 'F#4', 'A4'],
      ['D5', 'B4', 'G4', 'B4'], ['A5', 'F#5', 'D5', 'F#5'], ['D5', 'B4', 'G4', 'B4'], ['E5', 'C#5', 'A4', 'C#5']]
V5 = [['D5', 'E5', 'F#5', 'G5'], ['A5', 'G5', 'F#5', 'E5'], ['D5', 'E5', 'F#5', 'D5'], ['C#5', 'D5', 'E5', 'C#5'],
      ['B4', 'C#5', 'D5', 'B4'], ['A4', 'B4', 'C#5', 'A4'], ['B4', 'C#5', 'D5', 'B4'], ['C#5', 'D5', 'E5', 'C#5']]
# 周ごとの構成: (主旋律, 第2声, ドラム, ストリングス重ね)
PLAN = [
    (V0, None, False, False),
    (V1, None, True,  False),
    (V2, None, True,  False),
    (V3, V1,   True,  False),
    (V4, V2,   True,  True),
    (V5, V3,   True,  True),
    (V2, V0,   True,  True),
    (V0, None, True,  False),
    (V1, None, False, False),
]

def add(buf, start_s, sig, pan=0.0):
    """pan: -1(L) .. 1(R)"""
    s = int(start_s * SR); e = min(s + len(sig), buf.shape[1])
    if e <= s: return
    gl, gr = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    buf[0, s:e] += gl * sig[:e - s]; buf[1, s:e] += gr * sig[:e - s]

def piano(f, dur, vel=1.0):
    n = int((dur + 0.6) * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for h in range(1, 8):
        fh = f * h * (1 + 0.0004 * h * h)      # わずかな非整数倍音(ピアノらしさ)
        if fh > 18000: break
        sig += (1 / h ** 1.1) * np.sin(2 * np.pi * fh * t) * np.exp(-t * (2.0 + 1.1 * h))
    gate = np.ones(n, dtype=np.float32)
    rel = int(0.25 * SR); nd = int(dur * SR)
    gate[nd:nd + rel] = np.linspace(1, 0, rel)[:max(0, min(rel, n - nd))]; gate[nd + rel:] = 0
    atk = int(0.004 * SR); gate[:atk] *= np.linspace(0, 1, atk)
    return (sig * gate * vel * 0.35).astype(np.float32)

def strings(f, dur, vel=1.0):
    n = int((dur + 0.5) * SR); t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.3 * t) * np.clip(t / 0.4, 0, 1)
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.006, 0.0, 0.006):
        for h in range(1, 9):
            sig += (1 / h ** 1.6) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + h * det * 50)
    env = np.ones(n, dtype=np.float32)
    atk = int(0.18 * SR); rel = int(0.45 * SR); nd = int(dur * SR)
    env[:atk] = np.linspace(0, 1, atk)
    env[nd:nd + rel] = np.linspace(1, 0, rel)[:max(0, min(rel, n - nd))]; env[nd + rel:] = 0
    return (sig * env * vel * 0.12).astype(np.float32)

def bass(f, dur, vel=1.0):
    n = int((dur + 0.1) * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 6) + 0.2 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 9)
    env = np.exp(-t * 1.5); nd = int(dur * SR); rel = int(0.06 * SR)
    env[nd:nd + rel] *= np.linspace(1, 0, rel)[:max(0, min(rel, n - nd))]; env[nd + rel:] = 0
    atk = int(0.006 * SR); env[:atk] *= np.linspace(0, 1, atk)
    return (sig * env * vel * 0.5).astype(np.float32)

def kick(vel=1.0):
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 48 + 130 * np.exp(-t / 0.045)
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    return (sig * vel * 0.9).astype(np.float32)

def clap(rng, vel=1.0):
    n = int(0.25 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    noise = noise - np.convolve(noise, np.ones(14) / 14, mode='same')  # 低域を削る
    env = np.zeros(n, dtype=np.float32)
    for k, off in enumerate((0.0, 0.011, 0.023)):
        s = int(off * SR); env[s:] += np.exp(-(t[:n - s]) / 0.012) * (0.8 if k else 1.0)
    env += np.exp(-t / 0.07) * 0.5
    return (noise * env * vel * 0.33).astype(np.float32)

def hat(rng, dur=0.045, vel=1.0):
    n = int(0.12 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    noise = noise - np.convolve(noise, np.ones(6) / 6, mode='same')
    return (noise * np.exp(-t / dur) * vel * 0.16).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.22):
    out = np.empty_like(x)
    taps = [((1553, 0.70), (1877, 0.68), (2251, 0.66), (3011, 0.60)), ((1601, 0.70), (1931, 0.68), (2311, 0.66), (3089, 0.60))]
    for ch in range(2):
        wet = sum(comb(x[ch], d, g) for d, g in taps[ch]) / 4
        # ウェット成分の高域を少し落とす
        wet = np.convolve(wet, np.ones(5) / 5, mode='same')
        out[ch] = (1 - mix) * x[ch] + mix * wet
    return out

def play_var(buf, var, t_start, inst, pan, vel, octave=0, canon_delay=0.0):
    for ci, notes in enumerate(var):
        step = CHORD / len(notes)
        for k, nm in enumerate(notes):
            f = midi(N[nm] + 12 * octave)
            add(buf, t_start + canon_delay + ci * CHORD + k * step, inst(f, step * 0.95, vel), pan)

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    lead = np.zeros((2, n), dtype=np.float32); acc = np.zeros((2, n), dtype=np.float32)
    low = np.zeros((2, n), dtype=np.float32); drums = np.zeros((2, n), dtype=np.float32)
    ncyc = int(np.ceil(total / CYCLE)) + 1
    for c in range(ncyc):
        t0 = c * CYCLE
        if t0 > total: break
        mel, second, drum_on, str_on = PLAN[min(c, len(PLAN) - 1)]
        # 主旋律(ピアノ、やや右)
        play_var(lead, mel, t0, piano, 0.18, 1.0)
        # ストリングスで主旋律を重ねる
        if str_on:
            play_var(acc, mel, t0, strings, -0.1, 0.7)
        # 第2声(半周遅れで追いかける = カノン)
        if second is not None:
            play_var(acc, second, t0, strings, -0.35, 0.8, octave=-1, canon_delay=4 * CHORD)
        for ci in range(8):
            tc = t0 + ci * CHORD
            # 伴奏コード(ピアノ、左寄り)
            for j, nm in enumerate(CHORDS[ci]):
                add(acc, tc + (0.0 if c > 0 else 0.0) + j * 0.012, piano(midi(N[nm]), CHORD * 0.9, 0.42), -0.25)
                if drum_on:
                    add(acc, tc + BEAT + j * 0.012, piano(midi(N[nm]), BEAT * 0.8, 0.28), -0.25)
            # ベース
            fb = midi(N[BASS[ci]])
            add(low, tc, bass(fb, BEAT * 0.9, 1.0))
            if drum_on:
                add(low, tc + BEAT, bass(fb * 2, BEAT * 0.45, 0.6))
                add(low, tc + 1.5 * BEAT, bass(fb, BEAT * 0.45, 0.7))
            # ドラム
            if drum_on:
                add(drums, tc, kick(1.0)); add(drums, tc + BEAT, clap(rng, 0.9), 0.1)
                if ci % 2 == 1: add(drums, tc + 1.5 * BEAT, kick(0.6))
                for k in range(4):
                    add(drums, tc + k * BEAT / 2, hat(rng, 0.03 if k % 2 == 0 else 0.07, 0.8 if k % 2 == 0 else 0.6), 0.3)
            elif c > 0 or ci >= 4:
                for k in range(4):
                    add(drums, tc + k * BEAT / 2, hat(rng, 0.03, 0.45), 0.3)
    mix = lead * 0.9 + acc * 1.0 + low * 0.8 + drums * 0.8
    mix = reverb(mix, 0.2)
    # フェードイン/アウト
    fi = int(0.8 * SR); fo = int(3.0 * SR)
    mix[:, :fi] *= np.linspace(0, 1, fi); mix[:, -fo:] *= np.linspace(1, 0, fo) ** 1.5
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x.T, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 66.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    write_wav(out, x)
    print('wrote', out, f'{x.shape[1] / SR:.1f}s')
