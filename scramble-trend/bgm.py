# -*- coding: utf-8 -*-
"""ドキュメンタリー風BGMをプログラムで合成する(外部音源不要・権利フリー)。
Dマイナー / 72BPM。低音ドローン + 倍音パッド + 和太鼓風の低い打音 + まばらな高音アルペジオ + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 84
BEAT = 60.0 / BPM
BAR = BEAT * 4

# コード進行(MIDIノート)。8小節でループ
PROG = [
    [50, 53, 57, 62],  # Dm
    [46, 50, 53, 58],  # Bb
    [53, 57, 60, 65],  # F
    [48, 52, 55, 60],  # C
    [50, 53, 57, 62],  # Dm
    [46, 50, 53, 58],  # Bb
    [43, 46, 50, 55],  # Gm
    [45, 49, 52, 57],  # A
]
ROOTS = [50, 46, 53, 48, 50, 46, 43, 45]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    """アタック a 秒・リリース r 秒の台形エンベロープ"""
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.002 * np.sin(2 * np.pi * 0.23 * t + rng.uniform(0, 6.28))
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.004, 0.004):
        for h in range(1, 7):
            sig += (1 / h ** 1.7) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + rng.uniform(0, 6.28))
    return sig

def taiko(f0=85.0, dur=0.7, rng=None):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 45 + (f0 - 45) * np.exp(-t / 0.08)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t / 0.22)
    click = rng.standard_normal(n).astype(np.float32) * np.exp(-t / 0.012)
    click = np.convolve(click, np.ones(96) / 96, mode='same')  # 高域を抑えて柔らかく
    return (body + 0.25 * click).astype(np.float32)

def pluck(f, dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.35)).astype(np.float32)

def comb(x, delay, g):
    """フィードバックコム: y[n] = x[n] + g*y[n-delay](ブロック処理で高速化)"""
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.72), (1877, 0.70), (2251, 0.68), (12007, 0.45))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=7):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pad = np.zeros(n, dtype=np.float32); drone = np.zeros(n, dtype=np.float32)
    hits = np.zeros(n, dtype=np.float32); arp = np.zeros(n, dtype=np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; chord = PROG[b % 8]
        # パッド(次の小節へ 1.2 秒かけてクロスフェード)
        dur = BAR + 1.2
        sig = sum(pad_note(midi(m), dur, rng) * (0.9 if i < 3 else 0.45) for i, m in enumerate(chord))
        add(pad, t0, sig * env_ar(len(sig), 1.0, 1.2))
        # ドローン(ルート 2 オクターブ下)
        f = midi(ROOTS[b % 8] - 24); tt = np.arange(int(dur * SR)) / SR
        d = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * 2 * f * tt)) * (1 + 0.15 * np.sin(2 * np.pi * 0.11 * tt))
        add(drone, t0, d.astype(np.float32) * env_ar(len(d), 1.0, 1.2))
        # 和太鼓風の打音: 1 拍目と 3 拍目(10 秒以降)、後半は裏拍にも弱く
        inten = min(1.0, max(0.0, (t0 - 8) / 20))
        if inten > 0:
            add(hits, t0, taiko(rng=rng) * inten)
            add(hits, t0 + 2 * BEAT, taiko(f0=75, rng=rng) * 0.7 * inten)
            if t0 > 30:
                add(hits, t0 + 3.5 * BEAT, taiko(f0=70, dur=0.4, rng=rng) * 0.35 * inten)
        # アルペジオ(18 秒以降、まばらに)
        if t0 > 18:
            for k in range(8):
                if rng.random() < 0.45:
                    m = chord[rng.integers(0, 4)] + 24
                    add(arp, t0 + k * BEAT / 2, pluck(midi(m)) * rng.uniform(0.5, 1.0))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * norm(pad) + 0.35 * norm(drone) + 0.8 * norm(hits) + 0.18 * reverb(norm(arp), 0.5)
    mix = reverb(mix, 0.18)
    # 全体: 2 秒フェードイン、最後 4 秒フェードアウト
    mix *= env_ar(len(mix), 2.0, 4.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 71.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
