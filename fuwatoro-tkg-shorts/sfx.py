# -*- coding: utf-8 -*-
"""演出用の効果音を numpy で合成する(権利フリー)。mix.py から利用。"""
import numpy as np
from dsp import *

def _t(dur): n = int(dur * SR); return n, np.arange(n) / SR

def whoosh(rng, dur=0.4, up=True):
    n, t = _t(dur); x = noise(n, rng)
    p = t / dur
    sweep = (p if up else 1 - p)
    # 時間変化するバンドパス: 短いブロックごとに FFT フィルタ
    out = np.zeros(n, np.float32); B = 1024
    for s in range(0, n, B):
        e = min(s + B, n); c = 300 + 5000 * sweep[s] ** 2
        out[s:e] = fft_filter(np.concatenate([x[s:e], np.zeros(B)]), lo=c * 0.6, hi=c * 1.8)[:e - s]
    env = np.sin(np.pi * p) ** 1.5
    return norm(out * env, 0.7)

def pop(rng, f=900, dur=0.09):
    n, t = _t(dur); f_t = f * (1 + 0.6 * np.exp(-t / 0.01))
    x = np.sin(2 * np.pi * np.cumsum(f_t) / SR) * np.exp(-t / 0.025)
    return norm(x, 0.6)

def ding(rng, f=1760, dur=0.9):
    n, t = _t(dur)
    x = sum(np.sin(2 * np.pi * f * r * t) * np.exp(-t / (0.35 / (i + 1))) / (i + 1) for i, r in enumerate((1, 2.76, 5.4)))
    return norm(x * env_ar(n, 0.002, 0.1), 0.5)

def crack(rng):
    n, t = _t(0.3)
    x = fft_filter(noise(n, rng), lo=1500) * np.exp(-t / 0.012)
    x += fft_filter(noise(n, rng), lo=600, hi=3000) * np.exp(-np.maximum(t - 0.03, 0) / 0.02) * (t > 0.03) * 0.8
    x += np.sin(2 * np.pi * 110 * t) * np.exp(-t / 0.05) * 0.5
    return norm(x, 0.7)

def stir(rng, dur=0.22):
    n, t = _t(dur)
    x = fft_filter(noise(n, rng), lo=800, hi=4500) * np.sin(np.pi * t / dur) ** 2
    return norm(x, 0.35)

def plop(rng):
    n, t = _t(0.25); f_t = 420 * np.exp(-t / 0.05) + 110
    x = np.sin(2 * np.pi * np.cumsum(f_t) / SR) * np.exp(-t / 0.07)
    x += fft_filter(noise(n, rng), lo=2000, hi=8000) * np.exp(-t / 0.02) * 0.3
    return norm(x, 0.75)

def drip(rng, f=1500):
    n, t = _t(0.12); f_t = f * (1 + 0.8 * np.exp(-t / 0.012))
    x = np.sin(2 * np.pi * np.cumsum(f_t) / SR) * np.exp(-t / 0.03)
    return norm(x, 0.5)

def sparkle(rng, base=1046.5):
    n, t = _t(1.1); x = np.zeros(n, np.float32)
    for i, r in enumerate((1, 1.25, 1.5, 2, 2.5, 3)):
        s = int(i * 0.055 * SR)
        x[s:] += (np.sin(2 * np.pi * base * r * t[:n - s]) * np.exp(-t[:n - s] / 0.3)).astype(np.float32)
    return norm(fft_filter(x, lo=600), 0.45)

def boom(rng):
    n, t = _t(0.9); f_t = 40 + 110 * np.exp(-t / 0.06)
    x = np.sin(2 * np.pi * np.cumsum(f_t) / SR) * np.exp(-t / 0.3)
    x += fft_filter(noise(n, rng), hi=400) * np.exp(-t / 0.15) * 0.5
    return norm(x, 0.85)

def tick(rng):
    n, t = _t(0.05)
    return norm(fft_filter(noise(n, rng), lo=2500, hi=7000) * np.exp(-t / 0.006), 0.4)

def stamp(rng):
    """ドンッ(判子/スタンプ)"""
    n, t = _t(0.45); x = np.sin(2 * np.pi * (70 + 150 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.12)
    x += fft_filter(noise(n, rng), lo=200, hi=2500) * np.exp(-t / 0.015)
    return norm(x, 0.85)

def sizzle_melt(rng, dur=1.0):
    """バターがじゅわっと溶ける"""
    n, t = _t(dur); x = fft_filter(noise(n, rng), lo=3000) * np.exp(-t / 0.5) * (1 + 0.5 * np.sin(2 * np.pi * 9 * t))
    return norm(x, 0.3)

def squish(rng):
    """ふわっ(柔らかいもの)"""
    n, t = _t(0.35); x = fft_filter(noise(n, rng), lo=250, hi=1200) * np.sin(np.pi * t / 0.35) ** 2
    return norm(x, 0.45)

def swell(rng, dur=0.6):
    """じゃーん(明るいコード)"""
    n, t = _t(dur); x = sum(np.sin(2 * np.pi * midi(m) * t) * 0.3 for m in (72, 76, 79, 84))
    return norm(x * env_ar(n, 0.02, 0.4), 0.5)
