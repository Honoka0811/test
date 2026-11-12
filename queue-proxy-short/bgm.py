# -*- coding: utf-8 -*-
"""明るいポップ系BGMをプログラムで合成する(外部音源不要・権利フリー)。
Fメジャー / 116BPM / F-C-Dm-Bb。キック・クラップ・ハイハット + ベース + マリンバ風コード + ベル風メロディ。
ステレオ (N, 2) の float32 を返す。単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 116
BEAT = 60.0 / BPM
BAR = BEAT * 4

PROG = [[65, 69, 72], [60, 64, 67], [62, 65, 69], [58, 62, 65]]   # F C Dm Bb
ROOTS = [41, 36, 38, 34]
# メロディ(小節ごとに 8 分音符 8 個、None は休符)。F メジャー・ペンタトニック中心
MELODY = [
    [77, None, 76, 77, 79, None, 77, None], [76, None, 72, None, 74, 76, None, None],
    [74, None, 77, 76, 74, None, 72, None], [70, None, 72, 74, 72, None, None, None],
    [77, None, 79, 81, 79, None, 77, 76], [76, None, 79, None, 76, 74, 72, None],
    [74, 76, 77, None, 81, None, 79, 77], [74, None, 72, None, 70, None, None, None],
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig, pan=0.0):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e <= s: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[s:e, 0] += sig[:e - s] * l * 1.414
    buf[s:e, 1] += sig[:e - s] * r * 1.414

def tt(dur): return np.arange(int(dur * SR)) / SR

def kick():
    t = tt(0.35); f = 50 + 110 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def noise_hit(rng, dur, decay, hp=True):
    n = rng.standard_normal(int(dur * SR)).astype(np.float32)
    if hp: n = np.diff(n, prepend=0)   # 簡易ハイパス
    return n * np.exp(-tt(dur) / decay).astype(np.float32)

def clap(rng):
    x = noise_hit(rng, 0.25, 0.06)
    x = np.convolve(x, np.ones(8) / 8, mode='same')
    env = np.ones_like(x)
    for k in (0.0, 0.011, 0.022):     # 3 回のバースト
        s = int(k * SR); env[s:s + 60] *= 1.8
    return x * env

def bass(f, dur):
    t = tt(dur)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    env = np.minimum(1, t / 0.005) * np.exp(-t / 0.25)
    return (s * env).astype(np.float32)

def marimba(f, dur=0.5):
    t = tt(dur)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.18) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.03)
    return (s * np.minimum(1, t / 0.002)).astype(np.float32)

def bell(f, dur=0.9):
    t = tt(dur)
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 1.2 * np.exp(-t / 0.15)   # 簡易 FM
    s = np.sin(2 * np.pi * f * t + mod) * np.exp(-t / 0.35)
    return (s * np.minimum(1, t / 0.003)).astype(np.float32)

def delay(x, sec, fb, mix):
    d = int(sec * SR); y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += fb * y[s - d:e - d]
    return (1 - mix) * x + mix * (y - x)

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR
    drums = np.zeros((n, 2), np.float32); bs = np.zeros((n, 2), np.float32)
    keys = np.zeros((n, 2), np.float32); mel = np.zeros((n, 2), np.float32)
    k_, nbars = kick(), int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; ci = b % 4
        last = t0 + BAR > total - BAR          # 最後の 1 小節はドラムを抜く
        intro = b < 2                          # 最初の 2 小節はキックなし
        for q in range(4):
            if not intro and not last: add(drums, t0 + q * BEAT, k_ * 0.9)
            if q in (1, 3) and not intro and not last: add(drums, t0 + q * BEAT, clap(rng) * 0.35, 0.1)
        for e in range(8):
            if not last:
                add(drums, t0 + e * BEAT / 2, noise_hit(rng, 0.06, 0.012) * (0.10 if e % 2 else 0.06), -0.3)
            # ベース: 8 分のルート、裏でオクターブ
            if not intro:
                f = midi(ROOTS[ci] + (12 if e % 2 else 0))
                add(bs, t0 + e * BEAT / 2, bass(f, BEAT / 2 * 0.95) * (0.55 if e % 2 else 0.8))
        # マリンバ風コード(裏拍)
        for q in range(4):
            for i, m in enumerate(PROG[ci]):
                add(keys, t0 + q * BEAT + BEAT / 2, marimba(midi(m)) * 0.33, -0.4 + 0.4 * i)
        # メロディ(3 小節目から)
        if b >= 2 and not last:
            for e, m in enumerate(MELODY[(b - 2) % 8]):
                if m is not None:
                    add(mel, t0 + e * BEAT / 2, bell(midi(m)) * 0.45, 0.25)
    for c in range(2):
        mel[:, c] = delay(mel[:, c], BEAT * (0.75 if c else 0.5), 0.35, 0.3)
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.75 * norm(drums) + 0.7 * norm(bs) + 0.5 * norm(keys) + 0.45 * norm(mel)
    mix = mix[:int(total * SR)]
    # 1 秒フェードイン、最後 2.5 秒フェードアウト
    m = len(mix); env = np.ones(m, np.float32)
    fi, fo = SR, int(2.5 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    mix *= env[:, None]
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)    # 軽いサチュレーションで角を丸める
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 58.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
