# -*- coding: utf-8 -*-
"""「ちょっと怪しげでポップ」なBGMを numpy だけで合成する(外部音源不使用・権利フリー)。
Aマイナー / 104BPM。ピチカート風ベース + プラック・アルペジオ + ベル(FM)の短いモチーフ
+ ソフトなキック / スナップ / シェイカー + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 104
BEAT = 60.0 / BPM
BAR = BEAT * 4

# 4小節ループ: Am - F - Dm - E
CHORDS = [[57, 60, 64], [53, 57, 60], [50, 53, 57], [52, 56, 59]]
BASS = [  # 小節ごとの 8分音符ベース(None=休符)
    [45, None, 52, None, 45, 47, 48, None],
    [41, None, 48, None, 41, 43, 45, None],
    [38, None, 45, None, 38, 40, 41, None],
    [40, None, 47, None, 40, None, 44, 47],
]
# ベルのモチーフ(拍位置, MIDI)  2小節で一回、2周目は少し変える
MOTIF_A = [(0, 76), (0.5, 79), (1, 76), (2, 75), (3, 72)]
MOTIF_B = [(0, 76), (0.5, 79), (1, 81), (1.5, 79), (2, 76), (3, 71)]


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]


def tt(dur): return np.arange(int(dur * SR)) / SR


def pizz(f, dur=0.45):
    t = tt(dur)
    s = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) + 0.15 * np.sin(2 * np.pi * 3 * f * t)
    env = (1 - np.exp(-t / 0.003)) * np.exp(-t / 0.11)
    return (s * env).astype(np.float32)


def pluck(f, dur=0.6):
    t = tt(dur)
    s = sum((0.6 ** k) * np.sin(2 * np.pi * f * (k + 1) * t) for k in range(4))
    return (s * np.exp(-t / 0.16) * (1 - np.exp(-t / 0.002))).astype(np.float32)


def bell(f, dur=1.6):
    t = tt(dur)
    mod = 1.8 * np.exp(-t / 0.35) * np.sin(2 * np.pi * f * 3.5 * t)
    s = np.sin(2 * np.pi * f * t + mod)
    return (s * np.exp(-t / 0.55) * (1 - np.exp(-t / 0.002))).astype(np.float32)


def kick(dur=0.35):
    t = tt(dur)
    f = 48 + 90 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)).astype(np.float32)


def noise_hit(rng, dur, decay, smooth):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    lo = np.convolve(x, np.ones(smooth) / smooth, mode='same')
    return ((x - lo) * np.exp(-t / decay)).astype(np.float32)  # 簡易ハイパス


def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y


def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (2683, 0.64))) / 4
    return (1 - mix) * x + mix * wet


def env_ar(n, a, r):
    e = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    e[:na] = np.linspace(0, 1, na); e[n - nr:] = np.linspace(1, 0, nr)
    return e


def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    bass = np.zeros(n, np.float32); arp = np.zeros(n, np.float32); bel = np.zeros(n, np.float32)
    drums = np.zeros(n, np.float32); pad = np.zeros(n, np.float32)
    nbars = int(np.ceil(total / BAR)) + 1
    end_bar = int(total / BAR)  # 最後の小節はジャンと鳴らして終わる
    for b in range(nbars):
        t0 = b * BAR
        if t0 >= total: break
        ch = CHORDS[b % 4]
        if b >= end_bar - 0 and b == end_bar:
            for m in [45, 57, 60, 64, 69]:
                add(arp, t0, pluck(midi(m), 2.5) * 0.8)
            add(bel, t0, bell(midi(81), 2.5))
            add(drums, t0, kick())
            continue
        # パッド(柔らかい持続音、ごく薄く)
        d = BAR + 0.4; t = tt(d)
        p = sum(np.sin(2 * np.pi * midi(m) * t) + 0.3 * np.sin(2 * np.pi * 2 * midi(m) * t) for m in ch)
        add(pad, t0, (p * env_ar(len(t), 0.3, 0.4)).astype(np.float32))
        # ベース
        for k, m in enumerate(BASS[b % 4]):
            if m is not None:
                add(bass, t0 + k * BEAT / 2, pizz(midi(m)) * (1.0 if k % 2 == 0 else 0.75))
        # アルペジオ(2小節目以降、16分の上下)
        if b >= 1:
            notes = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12]
            for k in range(16):
                if k % 4 == 3 and rng.random() < 0.5: continue
                add(arp, t0 + k * BEAT / 4, pluck(midi(notes[k % 4]), 0.35) * (0.9 if k % 4 == 0 else 0.55))
        # ベルのモチーフ(4小節目以降、2小節ごと)
        if b >= 2 and b % 2 == 0:
            for beat, m in (MOTIF_A if (b // 2) % 2 == 0 else MOTIF_B):
                add(bel, t0 + beat * BEAT, bell(midi(m)) * 0.8)
        # ドラム(1小節目はシェイカーのみ)
        for k in range(8):
            add(drums, t0 + k * BEAT / 2 + 0.008, noise_hit(rng, 0.08, 0.018, 6) * (0.18 if k % 2 else 0.1))
        if b >= 1:
            add(drums, t0, kick()); add(drums, t0 + 2 * BEAT, kick() * 0.85)
            if b % 4 == 3: add(drums, t0 + 3.5 * BEAT, kick() * 0.6)
            for k in (1, 3):
                add(drums, t0 + k * BEAT, noise_hit(rng, 0.18, 0.05, 30) * 0.55)  # スナップ
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.55 * norm(bass) + 0.32 * norm(arp) + 0.30 * norm(bel) + 0.10 * norm(pad)
           + 0.42 * norm(drums))
    mix = reverb(mix, 0.2)
    mix *= env_ar(len(mix), 0.3, 1.5)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)


if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
