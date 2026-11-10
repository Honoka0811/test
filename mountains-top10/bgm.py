# -*- coding: utf-8 -*-
"""明るいアドベンチャー風BGMを numpy だけで合成する(外部音源なし・権利フリー)。
Cメジャー / 112BPM、C-G-Am-F の進行。パッド+プラック系アルペジオ+ベース+キック/クラップ/ハイハット+ベルの主旋律。
使い方: python3 bgm.py 秒数 出力.wav [イントロ秒]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 112
BEAT = 60 / BPM
BAR = BEAT * 4
CHORDS = [  # (ベース音, 和音) MIDI
    (36, [60, 64, 67]),  # C
    (43, [59, 62, 67]),  # G
    (45, [60, 64, 69]),  # Am
    (41, [60, 65, 69]),  # F
]
# 2小節で1フレーズのベル旋律(拍位置, MIDI, 長さ拍)  ペンタトニック中心
MELODY = [
    [(0, 76, 1), (1, 79, 1), (2, 81, 1.5), (3.5, 79, .5)],
    [(0, 76, 1), (1, 74, 1), (2, 72, 2)],
    [(0, 72, 1), (1, 74, 1), (2, 76, 1.5), (3.5, 79, .5)],
    [(0, 77, 1), (1, 76, 1), (2, 74, 2)],
]

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def env(n, a, r):
    e = np.ones(n, np.float32)
    na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if nr < n: e[-nr:] *= np.linspace(1, 0, nr)
    return e

def add(buf, t, x):
    s = int(t * SR)
    if s >= len(buf): return
    e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s]

def pluck(f, dur, bright=6):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for k in range(1, bright + 1):
        if f * k > SR / 2.2: break
        x += (1 / k) * np.sin(2 * np.pi * f * k * tt) * np.exp(-tt * (4 + 3 * k))
    return x * env(n, .004, .03)

def pad(f, dur):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for det in (-0.12, 0.12):  # わずかなデチューンで厚み
        ff = f * 2 ** (det / 12)
        for k in range(1, 5):
            x += (1 / k ** 2) * np.sin(2 * np.pi * ff * k * tt + k)
    return x * env(n, .35, .45) * .5

def bell(f, dur):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * tt) + .35 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 6)
         + .2 * np.sin(2 * np.pi * f * 4 * tt) * np.exp(-tt * 9))
    return (x * np.exp(-tt * 2.2) * env(n, .005, .08)).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * tt) + .3 * np.sin(2 * np.pi * f * 2 * tt)
    return (x * np.exp(-tt * 2.5) * env(n, .005, .06)).astype(np.float32)

def kick():
    n = int(.28 * SR); tt = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(45 + 90 * np.exp(-tt * 30)) / SR
    return (np.sin(ph) * np.exp(-tt * 12)).astype(np.float32)

rng = np.random.default_rng(7)
def clap():
    n = int(.22 * SR); tt = np.arange(n) / SR
    nz = rng.standard_normal(n).astype(np.float32)
    nz = nz - np.concatenate([[0], nz[:-1]]) * .6
    return nz * np.exp(-tt * 22) * .5

def hat():
    n = int(.06 * SR); tt = np.arange(n) / SR
    nz = rng.standard_normal(n).astype(np.float32)
    nz = np.diff(nz, prepend=0)
    return nz * np.exp(-tt * 70) * .25

def reverb(x, sec=1.4, mix=.22):
    n = int(sec * SR); tt = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-tt * 4.5)
    ir[:int(.02 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    L = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return (x + mix * wet).astype(np.float32)

def generate(total, intro=4.0):
    """total 秒の BGM を返す。intro 秒まではドラム無し、最後の 4 小節弱は穏やかに締める"""
    N = int(total * SR) + SR
    mus = np.zeros(N, np.float32); drm = np.zeros(N, np.float32)
    nbars = int(np.ceil(total / BAR)) + 1
    outro = total - 5.0
    for b in range(nbars):
        t0 = b * BAR
        if t0 > total: break
        root, ch = CHORDS[b % 4]
        full = intro <= t0 < outro
        for m in ch:
            add(mus, t0, pad(hz(m), BAR + .4) * .05)
        # アルペジオ(8分): 和音を上下に
        pat = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12, ch[2] + 12]
        for i, m in enumerate(pat):
            add(mus, t0 + i * BEAT / 2, pluck(hz(m), .6) * (.11 if i % 2 == 0 else .08))
        if t0 >= intro - BAR:
            for bt, ln in ((0, 1.5), (1.5, .5), (2, 1.5), (3.5, .5)):
                add(mus, t0 + bt * BEAT, bass(hz(root), ln * BEAT + .05) * .3)
        if full:
            for i in range(4): add(drm, t0 + i * BEAT, kick() * .55)
            for i in (1, 3): add(drm, t0 + i * BEAT, clap() * .35)
            for i in range(8):
                add(drm, t0 + (i + .5) * BEAT / 2 + (0 if i % 2 else 0), hat() * (.55 if i % 2 else .3))
            if t0 >= intro + 2 * BAR:  # 少し進んでから主旋律
                for bt, m, ln in MELODY[b % 4]:
                    add(mus, t0 + bt * BEAT, bell(hz(m), ln * BEAT + .6) * .11)
    # 最後のジャーン
    end_t = min(outro, total - 2.5)
    for m in CHORDS[0][1] + [72, 76]:
        add(mus, end_t + .01, pluck(hz(m), 3.0, 4) * .1)
    add(mus, end_t, kick() * .5)
    x = reverb(mus) + drm
    x = x[:int(total * SR)]
    x *= env(len(x), .8, 2.0)
    return (x / (np.max(np.abs(x)) + 1e-9) * .9).astype(np.float32)

def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 72
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    intro = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    write(out, generate(total, intro)); print('wrote', out)
