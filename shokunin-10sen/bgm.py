# -*- coding: utf-8 -*-
"""明るめのポップBGMを numpy だけで合成する(外部音源なし・権利フリー)。
使い方: python3 bgm.py [秒数] [出力wav]"""
import sys, wave
import numpy as np

SR = 48000
BPM = 124
BEAT = 60.0 / BPM

def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1.0) * np.exp(-np.maximum(t - a, 0) / d)

def _note(freq, dur, kind):
    n = int(dur * SR); t = np.arange(n) / SR
    if kind == 'pluck':   # マリンバ風
        x = np.sin(2*np.pi*freq*t) + 0.35*np.sin(2*np.pi*freq*4*t) * np.exp(-t/0.03)
        return x * _env(n, 0.003, 0.16)
    if kind == 'pad':     # コード
        x = sum(np.sin(2*np.pi*freq*k*t) / k**1.6 for k in (1, 2, 3, 4))
        return x * _env(n, 0.01, 0.22)
    if kind == 'bass':
        x = np.sin(2*np.pi*freq*t) + 0.4*np.sin(2*np.pi*freq*2*t) + 0.15*np.sin(2*np.pi*freq*3*t)
        return x * _env(n, 0.005, 0.20)

def _kick():
    n = int(0.28 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.035)
    return np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t / 0.11)

def _noise(rng, dur, decay, hp):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    for _ in range(hp): x = np.diff(x, prepend=0)   # 簡易ハイパス
    x /= np.max(np.abs(x))
    return x * np.exp(-t / decay)

def _add(buf, x, t0, g):
    s = int(t0 * SR)
    if s >= len(buf): return
    e = min(s + len(x), len(buf)); buf[s:e] += x[:e - s] * g

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def generate(total):
    rng = np.random.default_rng(7)
    buf = np.zeros(int(total * SR) + SR, dtype=np.float64)
    # 王道進行 F - G - Em - Am (MIDI)
    chords = [(53, [65, 69, 72]), (55, [67, 71, 74]), (52, [64, 67, 71]), (57, [69, 72, 76])]
    arp = [0, 1, 2, 1, 2, 1, 0, 2]
    kick, hat, clap = _kick(), _noise(rng, 0.05, 0.012, 2), _noise(rng, 0.16, 0.05, 1)
    bars = int(total / (BEAT * 4)) + 1
    for b in range(bars):
        t0 = b * BEAT * 4
        root, tri = chords[b % 4]
        full = b >= 2            # 最初の2小節はドラム抜き
        for q in range(4):
            tb = t0 + q * BEAT
            if full:
                _add(buf, kick, tb, 0.9)
                if q in (1, 3): _add(buf, clap, tb, 0.28)
            _add(buf, _note(hz(root - 12), BEAT * 0.5, 'bass'), tb, 0.42)
            _add(buf, _note(hz(root), BEAT * 0.5, 'bass'), tb + BEAT / 2, 0.30)
            for m in tri:        # 裏拍のコード
                _add(buf, _note(hz(m - 12), BEAT * 0.5, 'pad'), tb + BEAT / 2, 0.10)
        for e in range(8):
            te = t0 + e * BEAT / 2
            if full: _add(buf, hat, te, 0.16 if e % 2 else 0.09)
            m = tri[arp[(e + b) % 8]] + (12 if (e + b * 3) % 5 == 0 else 0)
            _add(buf, _note(hz(m), BEAT * 0.5, 'pluck'), te, 0.20)
    buf = buf[:int(total * SR)]
    f = int(0.4 * SR); buf[:f] *= np.linspace(0, 1, f)
    f = int(1.5 * SR); buf[-f:] *= np.linspace(1, 0, f)
    buf = np.tanh(buf * 1.2)
    return (buf / np.max(np.abs(buf)) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out)
