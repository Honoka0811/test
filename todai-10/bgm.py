# -*- coding: utf-8 -*-
"""明るいポップ系BGMを numpy だけで合成する(外部音源なし・権利フリー)。
Cメジャー / 118BPM。進行 C–G–Am–F。キック・クラップ・ハイハット・ベース・コードスタブ・ベル風メロディ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 118
BEAT = 60 / BPM
BAR = BEAT * 4
PROG = [[60, 64, 67], [59, 62, 67], [57, 60, 64], [57, 60, 65]]   # C, G/B, Am, F
ROOTS = [36, 43, 45, 41]
# 2小節で1フレーズのメロディ(16分音符グリッド, None=休符)
MEL = [
    [72, None, 76, None, 79, None, 76, 74, None, None, 72, None, 74, None, 76, None],
    [74, None, 71, None, 74, None, 79, None, 76, None, 74, None, 72, None, None, None],
    [72, None, 76, None, 81, None, 79, 76, None, None, 77, None, 76, None, 74, None],
    [72, None, 69, None, 72, None, 77, None, 76, None, 74, None, 72, None, None, None],
]

def midi(n): return 440 * 2 ** ((n - 69) / 12)

def add(buf, t, sig):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def tt(d): return np.arange(int(d * SR)) / SR

def kick():
    t = tt(0.35); f = 45 + 110 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def noise_hit(rng, d, decay, smooth):
    t = tt(d); n = rng.standard_normal(len(t))
    if smooth > 1: n = n - np.convolve(n, np.ones(smooth) / smooth, mode='same')   # 簡易ハイパス
    return (n * np.exp(-t / decay)).astype(np.float32)

def clap(rng):
    x = noise_hit(rng, 0.25, 0.06, 6)
    env = np.ones(len(x));
    for k in (0.0, 0.011, 0.022):                                           # 3回ばらけた打撃
        env[int(k * SR):int(k * SR) + 200] *= 1.6
    return (x * env).astype(np.float32)

def bass(f, d):
    t = tt(d)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    env = np.minimum(1, t / 0.005) * np.exp(-t / 0.35)
    return (s * env).astype(np.float32)

def stab(notes, d):
    t = tt(d); s = np.zeros(len(t))
    for n in notes:
        f = midi(n)
        for det in (-0.006, 0.0, 0.006):                                     # デチューンしたノコギリ波風
            for h in range(1, 6):
                s += np.sin(2 * np.pi * f * (1 + det) * h * t) / h * (0.8 ** h)
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.16)
    return (s * env).astype(np.float32)

def bell(f, d=0.9):
    t = tt(d)
    s = np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t / 0.15))  # FMベル
    return (s * np.exp(-t / 0.3) * np.minimum(1, t / 0.003)).astype(np.float32)

def delay(x, sec, fb, mix):
    d = int(sec * SR); y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += fb * y[s - d:e - d]
    return (1 - mix) * x + mix * y

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    tr = {k: np.zeros(n, np.float32) for k in ('kick', 'clap', 'hat', 'bass', 'stab', 'mel')}
    K = kick()
    s16 = BEAT / 4
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; ci = b % 4; chord = PROG[ci]
        intro = b < 2                                                         # 最初の2小節はドラム控えめ
        for beat in range(4):
            tb = t0 + beat * BEAT
            if not intro or beat == 0: add(tr['kick'], tb, K)
            if not intro and beat in (1, 3): add(tr['clap'], tb, clap(rng))
            for h in range(2):                                                # 8分ハイハット(裏拍を強く)
                add(tr['hat'], tb + h * BEAT / 2, noise_hit(rng, 0.06, 0.012, 3) * (1.0 if h else 0.5))
        # ベース: 8分でルート/オクターブ
        for k in range(8):
            f = midi(ROOTS[ci] + (12 if k % 4 == 3 else 0))
            add(tr['bass'], t0 + k * BEAT / 2, bass(f, BEAT / 2 * 0.95))
        # コードスタブ: 裏拍
        for k in (1, 3, 5, 7):
            add(tr['stab'], t0 + k * BEAT / 2, stab(chord, 0.3))
        # メロディ(4小節目以降)
        if b >= 4:
            for k, m in enumerate(MEL[b % 4]):
                if m is not None:
                    add(tr['mel'], t0 + k * s16, bell(midi(m)))
    def nz(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.75 * nz(tr['kick']) + 0.35 * nz(tr['clap']) + 0.12 * nz(tr['hat']) + 0.5 * nz(tr['bass'])
           + 0.28 * nz(delay(tr['stab'], BEAT * 0.75, 0.3, 0.25)) + 0.30 * nz(delay(tr['mel'], BEAT * 0.75, 0.35, 0.35)))
    fade = np.ones(n, np.float32)
    fi, fo = int(0.3 * SR), int(3.0 * SR)
    fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
    mix *= fade
    mix = np.tanh(mix * 1.2)                                                  # 軽いサチュレーション
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
