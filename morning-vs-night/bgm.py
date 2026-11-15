# -*- coding: utf-8 -*-
"""ポップで軽快なバトル風BGMと効果音をプログラムで合成する(外部音源不要・権利フリー)。
Cメジャー / 124BPM。キック + クラップ + ハイハット + ベース + 裏打ちコード + ベル系メロディ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 124
BEAT = 60.0 / BPM
BAR = BEAT * 4

# 8小節ループのコード進行(MIDI)。C G Am F / F G Em Am
PROG = [
    [60, 64, 67], [59, 62, 67], [57, 60, 64], [57, 60, 65],
    [57, 60, 65], [59, 62, 67], [59, 64, 67], [57, 60, 64],
]
ROOTS = [48, 43, 45, 41, 41, 43, 40, 45]
# メロディ(小節ごと 8分音符×8、None は休符)。コードトーン中心の明るいフレーズ
MELODY = [
    [72, None, 76, None, 79, 76, None, 74],
    [74, None, 71, None, 74, None, 79, None],
    [76, None, 72, None, 69, 72, None, 76],
    [77, None, 76, None, 72, None, None, None],
    [77, None, 81, None, 77, 76, None, 74],
    [74, None, 79, None, 74, None, 71, None],
    [71, None, 76, None, 79, 76, None, 71],
    [72, None, 69, None, 72, None, None, None],
]

rng = np.random.default_rng(11)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig, g=1.0):
    s = int(start_s * SR)
    if s >= len(buf): return
    e = min(s + len(sig), len(buf))
    buf[s:e] += g * sig[:e - s]

def tt(dur): return np.arange(int(dur * SR)) / SR

def smooth(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same')

def kick(dur=0.35):
    t = tt(dur)
    f = 48 + 110 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def clap(dur=0.22):
    t = tt(dur); n = rng.standard_normal(len(t))
    n = n - smooth(n, 12)                     # 低域カット
    n = smooth(n, 3)
    env = np.exp(-t / 0.05) * (1 + 0.6 * (np.sin(2 * np.pi * 90 * t) > 0) * (t < 0.03))
    return (n * env * 0.6).astype(np.float32)

def hat(dur=0.06, open_=False):
    t = tt(0.22 if open_ else dur); n = rng.standard_normal(len(t))
    n = np.diff(np.diff(n, prepend=0), prepend=0)   # 高域だけ残す
    return (n * np.exp(-t / (0.07 if open_ else 0.018)) * 0.25).astype(np.float32)

def bass(f, dur):
    t = tt(dur)
    s = sum((1 / h) * np.sin(2 * np.pi * f * h * t) for h in range(1, 7))   # ノコギリ波(帯域制限)
    env = np.minimum(1, t / 0.005) * np.exp(-t / 0.25)
    return (s * env * 0.5).astype(np.float32)

def stab(chord, dur=0.22):
    t = tt(dur); s = np.zeros(len(t))
    for m in chord:
        f = midi(m)
        for det in (-0.006, 0.006):
            s += sum((1 / h) * np.sin(2 * np.pi * f * (1 + det) * h * t) for h in (1, 3, 5, 7))  # 矩形波寄り
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.07)
    return (s * env / len(chord) * 0.35).astype(np.float32)

def bell(f, dur=0.6):
    t = tt(dur)
    s = np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t / 0.15))  # FM ベル
    return (s * np.minimum(1, t / 0.003) * np.exp(-t / 0.22)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.55))) / 3
    return (1 - mix) * x + mix * wet

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def generate(total):
    n = int(total * SR)
    drums = np.zeros(n, np.float32); bs = np.zeros(n, np.float32)
    ch = np.zeros(n, np.float32); mel = np.zeros(n, np.float32)
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; i = b % 8
        full = b >= 2                     # 最初の2小節はイントロ(キック少なめ)
        for k in range(4):
            if full or k == 0: add(drums, t0 + k * BEAT, kick(), 1.0)
            if full and k in (1, 3): add(drums, t0 + k * BEAT, clap(), 0.8)
        for k in range(8):
            add(drums, t0 + k * BEAT / 2, hat(open_=(k % 2 == 1)), 0.5 if k % 2 else 0.3)
        # ベース: 8分でルート、裏でオクターブ上
        for k in range(8):
            f = midi(ROOTS[i] - 12 + (12 if k % 2 else 0))
            add(bs, t0 + k * BEAT / 2, bass(f, BEAT / 2 * 0.95))
        # 裏打ちコード
        for k in range(4):
            add(ch, t0 + k * BEAT + BEAT / 2, stab(PROG[i]))
        # メロディ(4小節目以降)
        if b >= 4:
            for k, m in enumerate(MELODY[i]):
                if m is not None:
                    add(mel, t0 + k * BEAT / 2, bell(midi(m)))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.75 * norm(drums) + 0.55 * norm(bs) + 0.40 * reverb(norm(ch), 0.3) + 0.30 * reverb(norm(mel), 0.35)
    mix *= env_ar(len(mix), 0.3, 2.5)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

# ---------------- 効果音 ----------------
def sfx_impact():
    """ラウンド開始: シュッ + ドン"""
    t = tt(1.0); nz = rng.standard_normal(len(t))
    sweep = (nz - smooth(nz, 6)) * np.exp(-((t - 0.12) / 0.07) ** 2) * 0.5
    f = 40 + 90 * np.exp(-t / 0.06)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-np.maximum(t - 0.18, 0) / 0.3) * (t > 0.18)
    return (sweep + boom).astype(np.float32)

def sfx_win():
    """勝利: キラキラの上昇アルペジオ"""
    out = np.zeros(int(1.2 * SR), np.float32)
    for k, m in enumerate([72, 76, 79, 84]):
        add(out, k * 0.07, bell(midi(m), 0.9), 0.7)
        add(out, k * 0.07, bell(midi(m + 12), 0.6), 0.25)
    return reverb(out, 0.3)

def sfx_draw():
    """引き分け: ジャーン(2回)"""
    out = np.zeros(int(2.0 * SR), np.float32)
    for st, g in ((0.0, 0.7), (0.22, 1.0)):
        for m in (55, 60, 64, 67, 72):
            t = tt(1.4); f = midi(m)
            s = sum((1 / h) * np.sin(2 * np.pi * f * h * t) for h in range(1, 8)) * np.exp(-t / 0.5)
            add(out, st, s.astype(np.float32), g * 0.25)
    return reverb(out, 0.3)

def sfx_pop():
    """テキスト出現: ポン"""
    t = tt(0.15); f = 600 + 900 * np.exp(-t / 0.02)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04) * 0.5).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
