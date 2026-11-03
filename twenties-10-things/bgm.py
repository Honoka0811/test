# -*- coding: utf-8 -*-
"""BGM: J.S.バッハ「プレリュード ハ長調」(平均律クラヴィーア曲集 第1巻 第1番 BWV846)のポップ・アレンジを numpy だけで合成する。
原曲はパブリックドメイン。この編曲・演奏データは本リポジトリで作成したもの。
92BPM / ハ長調。ピアノのアルペジオ(原曲)+ 柔らかいパッド + ベース + 軽いドラム + ベル。
全パートが各小節の和音構成音だけを使うため、構造的に不協和音が出ない。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 92
BEAT = 60.0 / BPM
BAR = 4 * BEAT
SIXTEENTH = BEAT / 4

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
NAMES = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
def N(s):
    name, octv = s[:-1], int(s[-1])
    return 12 * (octv + 1) + NAMES[name]

# 原曲の各小節は 5 音 (n1 n2 n3 n4 n5) を「1 2 3 4 5 3 4 5」×2 の16分音符で分散する。
# 減七の和音が出る小節(12,14,22,23,28)は省き、明るい響きの小節だけでつないでいる。
BARS = [
    'C4 E4 G4 C5 E5',   # 1  C
    'C4 D4 A4 D5 F5',   # 2  Dm7/C
    'B3 D4 G4 D5 F5',   # 3  G7/B
    'C4 E4 G4 C5 E5',   # 4  C
    'C4 E4 A4 E5 A5',   # 5  Am/C
    'C4 D4 F#4 A4 D5',  # 6  D7/C
    'B3 D4 G4 D5 G5',   # 7  G/B
    'B3 C4 E4 G4 C5',   # 8  Cmaj7/B
    'A3 C4 E4 G4 C5',   # 9  Am7
    'D3 A3 D4 F#4 C5',  # 10 D7
    'G3 B3 D4 G4 B4',   # 11 G
    'F3 A3 D4 A4 D5',   # 13 Dm/F
    'E3 G3 C4 G4 C5',   # 15 C/E
    'E3 F3 A3 C4 F4',   # 16 Fmaj7/E
    'D3 F3 A3 C4 F4',   # 17 Dm7
    'G2 D3 G3 B3 F4',   # 18 G7
    'C3 E3 G3 C4 E4',   # 19 C
    'C3 G3 Bb3 C4 E4',  # 20 C7
    'F2 F3 A3 C4 E4',   # 21 Fmaj7
    'G2 F3 G3 B3 D4',   # 24 G7
    'G2 E3 G3 C4 E4',   # 25 C/G
    'G2 D3 G3 C4 F4',   # 26 G7sus
    'G2 D3 G3 B3 F4',   # 27 G7
    'G2 E3 G3 C4 G4',   # 29 C/G
    'G2 D3 G3 C4 F4',   # 30 G7sus
]
FINAL = 'C2 C3 E3 G3 C4 E4 G4 C5'   # 終止の C
PATTERN = [0, 1, 2, 3, 4, 2, 3, 4]

def add(buf, start_s, sig, pan=0.0):
    s = int(start_s * SR); e = min(s + len(sig), buf.shape[1])
    if e <= s: return
    gl, gr = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    buf[0, s:e] += gl * sig[:e - s]; buf[1, s:e] += gr * sig[:e - s]

def env_gate(n, dur, atk=0.004, rel=0.25):
    g = np.ones(n, dtype=np.float32)
    nd = int(dur * SR); nr = int(rel * SR); na = int(atk * SR)
    g[:na] *= np.linspace(0, 1, na)
    if nd < n:
        k = min(nr, n - nd); g[nd:nd + k] = np.linspace(1, 0, k); g[nd + k:] = 0
    return g

def piano(f, dur, vel=1.0):
    n = int((dur + 0.5) * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for h in range(1, 7):
        fh = f * h
        if fh > 16000: break
        sig += (1 / h ** 1.3) * np.sin(2 * np.pi * fh * t) * np.exp(-t * (1.8 + 1.0 * h))
    return (sig * env_gate(n, dur, 0.003, 0.22) * vel * 0.35).astype(np.float32)

def pad(f, dur, vel=1.0):
    n = int((dur + 0.6) * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.0025, 0.0, 0.0025):
        for h in range(1, 6):
            sig += (1 / h ** 1.9) * np.sin(2 * np.pi * f * h * (1 + det) * t + det * 400)
    return (sig * env_gate(n, dur, 0.35, 0.55) * vel * 0.10).astype(np.float32)

def bass(f, dur, vel=1.0):
    n = int((dur + 0.1) * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 5)
    return (sig * np.exp(-t * 1.2) * env_gate(n, dur, 0.006, 0.06) * vel * 0.5).astype(np.float32)

def bell(f, dur=1.2, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.5) + 0.3 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 9)
    return (sig * env_gate(n, dur, 0.002, 0.2) * vel * 0.2).astype(np.float32)

def kick(vel=1.0):
    n = int(0.3 * SR); t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12) * vel * 0.8).astype(np.float32)

def snare(rng, vel=1.0):
    n = int(0.22 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    noise = noise - np.convolve(noise, np.ones(10) / 10, mode='same')
    tone = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.05)
    return ((noise * np.exp(-t / 0.06) * 0.5 + tone * 0.5) * vel * 0.3).astype(np.float32)

def hat(rng, dur=0.03, vel=1.0):
    n = int(0.1 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    noise = noise - np.convolve(noise, np.ones(5) / 5, mode='same')
    return (noise * np.exp(-t / dur) * vel * 0.12).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.2):
    out = np.empty_like(x)
    taps = [((1553, 0.70), (1877, 0.68), (2251, 0.66), (3011, 0.60)), ((1601, 0.70), (1931, 0.68), (2311, 0.66), (3089, 0.60))]
    for ch in range(2):
        wet = sum(comb(x[ch], d, g) for d, g in taps[ch]) / 4
        wet = np.convolve(wet, np.ones(6) / 6, mode='same')
        out[ch] = (1 - mix) * x[ch] + mix * wet
    return out

def generate(total, seed=5):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pno = np.zeros((2, n), dtype=np.float32); pads = np.zeros((2, n), dtype=np.float32)
    low = np.zeros((2, n), dtype=np.float32); drums = np.zeros((2, n), dtype=np.float32); bells = np.zeros((2, n), dtype=np.float32)
    nb = len(BARS)
    for b in range(nb):
        t0 = b * BAR
        if t0 > total: break
        notes = [N(s) for s in BARS[b].split()]
        # ピアノ: 原曲の分散和音(16分音符)。拍頭を少し強く、左右に軽く振る
        for rep in range(2):
            for k, idx in enumerate(PATTERN):
                i = rep * 8 + k
                vel = 1.0 if k == 0 else (0.8 if k == 4 else 0.68)
                vel *= 1 + 0.04 * rng.standard_normal()
                f = midi(notes[idx])
                add(pno, t0 + i * SIXTEENTH, piano(f, SIXTEENTH * 1.9, vel), -0.3 + 0.6 * idx / 4)
        # パッド: 小節の和音を柔らかく持続
        # (長7度/短2度で隣り合う音はパッドからは外し、ピアノだけで鳴らす)
        held = []
        for idx in range(1, 5):
            if any((notes[idx] - h) % 12 in (1, 11) for h in held): continue
            held.append(notes[idx])
            add(pads, t0, pad(midi(notes[idx]), BAR * 0.98, 0.9), -0.2 + 0.1 * idx)
        # ベース: 最低音をオクターブ下げて拍にのせる
        fb = midi(notes[0] - 12 if notes[0] >= N('C3') else notes[0])
        add(low, t0, bass(fb, BEAT * 1.8, 1.0))
        add(low, t0 + 2 * BEAT, bass(fb, BEAT * 1.3, 0.8))
        if 4 <= b < nb - 1:
            add(low, t0 + 3.5 * BEAT, bass(fb, BEAT * 0.4, 0.6))
        # ベル: 小節のいちばん高い音を 1 オクターブ上で
        if 8 <= b < nb - 1:
            add(bells, t0, bell(midi(notes[4] + 12), 1.4, 0.9), 0.3)
            if b % 2 == 1:
                add(bells, t0 + 2 * BEAT, bell(midi(notes[2] + 12), 1.0, 0.6), -0.3)
        # ドラム: 5 小節目から。最後の小節は抜いて終止へ
        if 4 <= b < nb - 1:
            add(drums, t0, kick(1.0)); add(drums, t0 + 2 * BEAT, kick(0.9))
            add(drums, t0 + BEAT, snare(rng, 0.9), 0.05); add(drums, t0 + 3 * BEAT, snare(rng, 0.9), 0.05)
            if b % 4 == 3: add(drums, t0 + 3.5 * BEAT, kick(0.6))
            for k in range(8):
                add(drums, t0 + k * BEAT / 2, hat(rng, 0.03 if k % 2 == 0 else 0.06, 0.9 if k % 2 == 0 else 0.55), 0.35)
        elif b >= 2:
            for k in range(8):
                add(drums, t0 + k * BEAT / 2, hat(rng, 0.03, 0.45), 0.35)
    # 終止: C の和音を広げて持続
    tf = nb * BAR
    if tf < total:
        for j, s in enumerate(FINAL.split()):
            add(pno, tf + j * 0.03, piano(midi(N(s)), 3.0, 0.9 if j else 1.0), -0.3 + 0.08 * j)
            add(pads, tf, pad(midi(N(s)), 4.0, 0.8), -0.2 + 0.06 * j)
        add(low, tf, bass(midi(N('C2')), 3.0, 1.0))
        add(bells, tf, bell(midi(N('C6')), 2.5, 0.8), 0.2)
    mix = pno * 1.0 + pads * 1.0 + low * 0.8 + drums * 0.75 + bells * 0.8
    mix = reverb(mix, 0.2)
    fi = int(0.6 * SR); fo = int(2.5 * SR)
    mix[:, :fi] *= np.linspace(0, 1, fi); mix[:, -fo:] *= np.linspace(1, 0, fo) ** 1.5
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x.T, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 66.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    write_wav(out, x)
    print('wrote', out, f'{x.shape[1] / SR:.1f}s  bars={len(BARS)} ({len(BARS) * BAR:.1f}s) + final chord')
