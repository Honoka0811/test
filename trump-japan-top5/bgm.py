# -*- coding: utf-8 -*-
"""政治・ニュース解説系の緊張感あるBGMと効果音をプログラムで合成する(外部音源不要・権利フリー)。
Cマイナー / 100BPM。脈打つ8分のシンセベース + 秒針のようなチック + 低弦パッド + 鼓動キック
+ 小節頭のブラス・スタブ。後半ほど音数が増えて盛り上がる。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR = 48000
BPM = 100
BEAT = 60 / BPM
BAR = BEAT * 4
# i - VI - III - VII (Cm - Ab - Eb - Bb) を2周、最後は G(属和音)で緊張を残す
PROG = [[48, 51, 55], [44, 48, 51], [51, 55, 58], [46, 50, 53],
        [48, 51, 55], [44, 48, 51], [41, 44, 48], [43, 47, 50]]

def midi(n): return 440 * 2 ** ((n - 69) / 12)

def add(buf, t, sig):
    i = int(t * SR)
    if i >= len(buf) or i + len(sig) <= 0: return
    if i < 0: sig = sig[-i:]; i = 0
    e = min(i + len(sig), len(buf)); buf[i:e] += sig[:e - i]

def env(n, a, r, hold_decay=None):
    e = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[n - nr:] *= np.linspace(1, 0, nr)
    if hold_decay: e *= np.exp(-np.arange(n) / SR / hold_decay)
    return e

def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return (2 * ((f * t + phase) % 1.0) - 1).astype(np.float32)

def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR / 2.2) / (SR / 2), output='sos'), x).astype(np.float32)

def hp(x, fc, order=2):
    return sosfilt(butter(order, fc / (SR / 2), btype='high', output='sos'), x).astype(np.float32)

def reverb(x, mix=0.25):
    out = np.zeros_like(x)
    for d, g in ((1789, .74), (2137, .72), (2659, .70), (3301, .66)):
        out += lfilter([1.0], np.r_[1.0, np.zeros(d - 1), -g], x).astype(np.float32)
    return (1 - mix) * x + mix * hp(out / 4, 150)

def norm(x): return x / (np.max(np.abs(x)) + 1e-9)

def generate(total, breaks=(), seed=3):
    """breaks: [(開始, 終了)] の区間は音楽を止める(溜め演出)"""
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    bass, pad, tick, kick, stab = (np.zeros(n, dtype=np.float32) for _ in range(5))
    nbars = int(np.ceil(total / BAR)) + 1
    for b in range(nbars):
        t0 = b * BAR; ch = PROG[b % 8]
        inten = min(1.0, t0 / 40)            # 0→1 に徐々に盛り上げる
        # 8分刻みのベース(ルート、時々オクターブ)
        for k in range(8):
            m = ch[0] - 12 + (12 if k in (3, 7) and b % 2 else 0)
            nn = int(BEAT / 2 * SR * 0.9)
            s = saw(midi(m), nn) + 0.6 * saw(midi(m) * 1.005, nn)
            s = lp(s, 380 + 900 * inten * (k % 2 == 0)) * env(nn, 0.004, 0.05, 0.18)
            add(bass, t0 + k * BEAT / 2, s * (1.0 if k % 2 == 0 else 0.75))
        # 低弦パッド(のこぎり波を3本デチューン → ローパス)
        dur = BAR + 0.6; nn = int(dur * SR)
        s = np.zeros(nn, dtype=np.float32)
        for m in ch:
            for det in (-0.006, 0, 0.006):
                s += saw(midi(m) * (1 + det), nn, rng.random())
        s = lp(s, 1100, 2) * env(nn, 0.5, 0.6)
        add(pad, t0, s)
        # 秒針のようなチック(16分、拍頭を強く) — 序盤から鳴らして緊張感
        for k in range(16):
            nn = int(0.03 * SR)
            c = hp(rng.standard_normal(nn).astype(np.float32), 6000) * env(nn, 0.0005, 0.02, 0.006)
            add(tick, t0 + k * BEAT / 4, c * (1.0 if k % 4 == 0 else 0.35 * inten + 0.15))
        # 鼓動キック(1, 3拍)— 8秒以降
        if t0 >= 8:
            for k in (0, 2):
                nn = int(0.35 * SR); tt = np.arange(nn) / SR
                f = 45 + 90 * np.exp(-tt / 0.03)
                add(kick, t0 + k * BEAT, (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.12)).astype(np.float32))
        # ブラス・スタブ(2小節ごと、後半)
        if t0 >= 16 and b % 2 == 0:
            nn = int(0.9 * SR); s = np.zeros(nn, dtype=np.float32)
            for m in ch:
                for o in (-12, 0):
                    s += saw(midi(m + o), nn) + saw(midi(m + o) * 1.004, nn)
            s = lp(s, 1600) * env(nn, 0.01, 0.3, 0.35)
            add(stab, t0, s * inten)
    mix = (0.55 * norm(bass) + 0.42 * norm(pad) + 0.12 * norm(tick) + 0.6 * norm(kick) + 0.28 * norm(stab))
    mix = reverb(mix, 0.22)
    mix *= env(n, 0.6, 2.5)
    for a, e in breaks:                       # 溜め: 0.08 秒でカット、終端で復帰
        i, j = int(a * SR), int(e * SR); f = int(0.08 * SR)
        g = np.ones(n, dtype=np.float32)
        g[i:i + f] = np.linspace(1, 0, f); g[i + f:j] = 0
        mix *= g
    return (norm(mix) * 0.9).astype(np.float32)

# ---------------- 効果音 ----------------
def boom(big=False):
    """順位発表のインパクト: サブベースの落下 + ノイズ + 低いブラァム"""
    rng = np.random.default_rng(11)
    d = 2.6 if big else 1.6; n = int(d * SR); t = np.arange(n) / SR
    f = 38 + 110 * np.exp(-t / 0.06)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.7 if big else 0.45))
    nz = lp(rng.standard_normal(n).astype(np.float32), 2500) * np.exp(-t / 0.08)
    br = np.zeros(n, dtype=np.float32)
    for m in (36, 43, 48) + ((31,) if big else ()):
        br += saw(midi(m), n) + saw(midi(m) * 1.007, n)
    br = lp(br, 700) * env(n, 0.01, 0.8, 0.6 if big else 0.35)
    return reverb(norm(sub) + 0.5 * norm(nz) + (0.5 if big else 0.35) * norm(br), 0.3)

def whoosh():
    rng = np.random.default_rng(5)
    n = int(0.45 * SR); x = rng.standard_normal(n).astype(np.float32)
    # 帯域を上から下へスイープ(ブロック処理)
    out = np.zeros(n, dtype=np.float32); blk = 960
    for i in range(0, n, blk):
        p = i / n; fc = 7000 * (1 - p) + 400
        out[i:i + blk] = lp(x[max(0, i - 2000):i + blk], fc)[-len(x[i:i + blk]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2

def riser(d=1.4):
    rng = np.random.default_rng(9)
    n = int(d * SR); x = rng.standard_normal(n).astype(np.float32); out = np.zeros(n, dtype=np.float32); blk = 960
    for i in range(0, n, blk):
        p = i / n; fc = 300 + 8000 * p ** 2
        out[i:i + blk] = lp(x[max(0, i - 2000):i + blk], fc)[-len(x[i:i + blk]):]
    return out * np.linspace(0, 1, n) ** 2

def sfx_track(total, events):
    n = int(total * SR); out = np.zeros(n, dtype=np.float32)
    for e in events:
        if e['type'] == 'impact':
            if e.get('big'):
                add(out, e['t'] - 1.4 - 0.7, riser() * 0.5)      # 溜めの前に上昇音
            add(out, e['t'] - 0.02, boom(e.get('big', False)) * (1.0 if e.get('big') else 0.8))
        elif e['type'] == 'whoosh':
            add(out, e['t'] - 0.15, whoosh() * 0.35)
        elif e['type'] == 'boom':
            add(out, e['t'], boom(True) * 0.9)
    return out / max(1.0, np.max(np.abs(out)))

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
