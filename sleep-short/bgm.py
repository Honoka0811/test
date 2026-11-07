# -*- coding: utf-8 -*-
"""ショート用の chill-hop BGM と効果音をプログラムで合成する(外部音源なし・権利フリー)。
C メジャー / 88BPM。Fmaj7-Em7-Dm7-Cmaj7 のループ。展開はナレーションのタイミング(cues)に合わせる:
  ~drop     : 夜のパッドだけ(クイズの緊張感)、ローパスで籠もらせる
  drop~     : ビート + オルゴール旋律 + キックに合わせたポンプ感(ここで一気に引き込む)
  bright~   : 朝のシーン。高音のキラキラアルペジオを追加
  outro~    : ビートが抜けてオルゴールとパッドだけ → フェードアウト
"""
import numpy as np

SR = 48000
BPM = 88
BEAT = 60.0 / BPM
BAR = BEAT * 4
CHORDS = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]
BASS = [41, 40, 38, 36]
PENTA = [72, 74, 76, 79, 81, 84, 86, 88]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start, sig, gain=1.0):
    s = int(start * SR)
    if s < 0:  # 動画の開始より前に始まる音は、頭を切って鳴らす
        sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if s < len(buf) and e > s: buf[s:e] += sig[:e - s] * gain

def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)

def musicbox(f, dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.15) + 0.15 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t / 0.05)
    return (s * env(n, 0.002, 0.55)).astype(np.float32)

def pad(freqs, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f in freqs:
        for det in (-0.006, 0, 0.006):
            ph = rng.uniform(0, 6.28)
            for h in range(1, 6):
                s += np.sin(2 * np.pi * f * h * (1 + det) * t + ph * h) / h ** 1.5
    e = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.6).clip(0)
    return (s * e).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t)) * env(n, 0.01, 0.8) * np.minimum(1, (dur - t) / 0.05).clip(0)).astype(np.float32)

def kick():
    n = int(0.4 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.025)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.14)).astype(np.float32)

def noise(rng, dur, decay, hp=4):
    n = int(dur * SR); x = rng.standard_normal(n)
    if hp > 1: x = x - np.convolve(x, np.ones(hp) / hp, mode='same')
    return (x * env(n, 0.001, decay)).astype(np.float32)

def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same').astype(np.float32) if k > 1 else x

def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y

def reverb(x, mix):
    wet = sum(comb(x, d, g) for d, g in ((1687, .72), (2053, .7), (2389, .68), (3221, .62))) / 4
    return (1 - mix) * x + mix * wet

def norm(x): return x / (np.max(np.abs(x)) + 1e-9)

def generate(total, cues, seed=5):
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR
    P, MB, SP, BS, DR = (np.zeros(n, np.float32) for _ in range(5))
    pump = np.ones(n, np.float32)
    drop, bright, outro = cues['drop'], cues['bright'], cues['outro']
    # ビートの頭をドロップ位置にそろえる(ドロップの瞬間に 1 拍目のキックが鳴る)
    t0 = drop - np.ceil(drop / BAR) * BAR
    motif = [(0, 4), (0.5, 3), (1, 2), (2, 3), (2.5, 4), (3, 5), (4, 4), (5, 2), (5.5, 1), (6, 2), (7, 0)]
    motif2 = [(0, 2), (0.5, 3), (1, 4), (2, 5), (3, 6), (4, 5), (4.5, 4), (5, 3), (6, 4), (6.5, 2)]
    b = 0
    while t0 + b * BAR < total:
        ts = t0 + b * BAR; ci = b % 4
        add(P, ts, pad([midi(m) for m in CHORDS[ci]], BAR + 0.6, rng), 1.0)
        beat_on = drop - 0.01 <= ts < outro - 0.01
        if beat_on:
            add(BS, ts, bass(midi(BASS[ci]), BEAT * 3), 1.0)
            add(BS, ts + BEAT * 3, bass(midi(BASS[ci] + 7), BEAT), 0.6)
            for k in (0, 1.75, 2.5):
                add(DR, ts + k * BEAT, kick(), 1.0)
                s = int((ts + k * BEAT) * SR); L = int(0.28 * SR)
                if 0 <= s < n - L: pump[s:s + L] = np.minimum(pump[s:s + L], 0.55 + 0.45 * np.linspace(0, 1, L) ** 0.6)
            for k in (1, 3):
                add(DR, ts + k * BEAT, noise(rng, 0.25, 0.07, 5), 0.45)
            for i in range(8):
                sw = 0.07 * BEAT if i % 2 else 0
                add(DR, ts + i * BEAT / 2 + sw, noise(rng, 0.05, 0.012, 2), 0.13 if i % 2 else 0.2)
        if ts >= drop - 0.01 and b % 2 == 0:
            mot = motif if (b // 2) % 2 == 0 else motif2
            for beat, idx in mot:
                add(MB, ts + beat * BEAT, musicbox(midi(PENTA[idx])), rng.uniform(0.7, 1.0))
        if ts >= bright - BAR:
            for i in range(16):
                if rng.random() < 0.6:
                    add(SP, ts + i * BEAT / 4, musicbox(midi(PENTA[rng.integers(3, 8)] + 12), 0.6), rng.uniform(0.3, 0.6))
        b += 1
    mix = (0.42 * norm(reverb(P, 0.3)) + 0.5 * norm(reverb(MB, 0.4)) + 0.25 * norm(reverb(SP, 0.5))) * pump
    mix += 0.55 * norm(lowpass(BS, 6)) + 0.5 * norm(DR)
    # ドロップまではローパスで籠もらせ、ドロップの瞬間に開く(期待感 → 解放)
    pre = int(drop * SR)
    mix[:pre] = lowpass(mix[:pre], 24) * 1.3
    # 静かなレコードノイズ
    crackle = (rng.random(n) < 0.0004) * rng.uniform(-1, 1, n)
    mix += 0.04 * lowpass(crackle.astype(np.float32), 3)
    mix = mix[:int(total * SR)]
    e = np.ones(len(mix), np.float32)
    fi, fo = int(0.3 * SR), int(1.5 * SR)
    e[:fi] = np.linspace(0, 1, fi); e[-fo:] = np.linspace(1, 0, fo)
    return (norm(mix * e) * 0.9).astype(np.float32)

# ---------- 効果音 ----------
def sfx_tick(rng):
    n = int(0.08 * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * 2400 * t) * 0.6 + noise(rng, 0.08, 0.004, 2)) * np.exp(-t / 0.012)).astype(np.float32)

def sfx_reveal():
    """正解発表の「ピンポン」"""
    out = np.zeros(int(0.9 * SR), np.float32)
    for st, f in ((0, midi(84)), (0.16, midi(79))):
        n = int(0.7 * SR); t = np.arange(n) / SR
        s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * env(n, 0.003, 0.25)
        add(out, st, s.astype(np.float32))
    return out

def sfx_whoosh(rng, dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n); k_prev = None
    # 時間とともにフィルタの幅を変えて「シュッ」とさせる(ブロック処理)
    blk = 960
    for s in range(0, n, blk):
        k = int(2 + 40 * (1 - s / n))
        out[s:s + blk] = np.convolve(x[max(0, s - k):s + blk], np.ones(k) / k, mode='same')[-len(out[s:s + blk]):]
    shape = np.sin(np.pi * t / dur) ** 2
    return (out * shape * 3).astype(np.float32)

def sfx_pop():
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 500 + 900 * np.exp(-t / 0.02)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035)).astype(np.float32)

def sfx_chime():
    out = np.zeros(int(1.2 * SR), np.float32)
    for i, m in enumerate((79, 83, 86, 91)):
        add(out, i * 0.06, musicbox(midi(m), 1.0), 0.8)
    return out

def sfx_sparkle(rng):
    out = np.zeros(int(1.6 * SR), np.float32)
    for i in range(14):
        add(out, i * 0.07 + rng.uniform(0, 0.02), musicbox(midi(int(rng.choice([88, 91, 93, 96, 98, 100]))), 0.5), 0.5 * (1 - i / 16))
    return out
