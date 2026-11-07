# -*- coding: utf-8 -*-
"""効果音を numpy で合成(権利フリー)。whoosh / pop / ding / sparkle / boom"""
import numpy as np
SR = 48000

def _hp(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * (1 - 1 / np.sqrt(1 + (f / fc) ** 4)), n=len(x)).astype(np.float32)
def _lp(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 4), n=len(x)).astype(np.float32)

def whoosh(dur=0.5, seed=0):
    rng = np.random.default_rng(seed); n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    noise = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, dtype=np.float32); B = 1024
    for s in range(0, n, B):
        seg = noise[s:s + B]; uu = s / n
        fc = 400 + 5000 * np.sin(np.pi * uu) ** 2
        out[s:s + len(seg)] = _hp(_lp(seg, fc * 2.5), fc * 0.5)
    env = (np.sin(np.pi * u) ** 1.5).astype(np.float32)
    return out * env * 0.9

def pop(f0=900.0, dur=0.09):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * np.exp(-t / 0.03) + 180
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.025)
    return x.astype(np.float32) * 0.9

def ding(f=1318.5, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.35) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.12)
         + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.06))
    return (x * 0.6).astype(np.float32)

def sparkle(dur=1.4, seed=3):
    rng = np.random.default_rng(seed); n = int(dur * SR); out = np.zeros(n, dtype=np.float32)
    for i in range(14):
        f = rng.choice([1760, 2093, 2637, 3136, 3520, 4186]); s = int(rng.uniform(0, dur * 0.7) * SR)
        m = int(0.5 * SR); t = np.arange(m) / SR
        tone = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.12) * 0.25
        e = min(s + m, n); out[s:e] += tone[:e - s]
    return out

def tick(dur=0.03):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.006)).astype(np.float32) * 0.5

def boom(dur=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 32 + 90 * np.exp(-t / 0.06)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.3)).astype(np.float32)
