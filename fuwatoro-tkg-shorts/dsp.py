# -*- coding: utf-8 -*-
"""bgm.py / sfx.py 共通の小さな DSP ユーティリティ(numpy のみ)"""
import numpy as np
SR = 48000

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig, gain=1.0):
    s = int(start_s * SR)
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * gain

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: env[:na] = np.linspace(0, 1, na)
    if nr: env[n - nr:] *= np.linspace(1, 0, nr)
    return env

def fft_filter(x, lo=None, hi=None, order=2.0):
    """FFT ベースの静的フィルタ。lo より下 / hi より上をなだらかに減衰させる(バターワース風)。"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = np.ones_like(f)
    if hi: H *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    if lo: H *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    return np.fft.irfft(X * H, n=len(x)).astype(np.float32)

def saw(f, n, harmonics=24):
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    for h in range(1, harmonics + 1):
        if f * h > SR / 2: break
        out += ((-1) ** (h + 1)) * np.sin(2 * np.pi * f * h * t) / h
    return out * (2 / np.pi)

def square(f, n, harmonics=15):
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    for h in range(1, harmonics + 1, 2):
        if f * h > SR / 2: break
        out += np.sin(2 * np.pi * f * h * t) / h
    return out * (4 / np.pi)

def noise(n, rng): return rng.standard_normal(n).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25, size=1.0):
    taps = ((1553, 0.72), (1877, 0.70), (2251, 0.68), (3061, 0.6))
    wet = sum(comb(x, int(d * size), g) for d, g in taps) / 4
    wet = fft_filter(wet, hi=6000)
    return (1 - mix) * x + mix * wet

def delay_fx(x, time_s, fb=0.35, mix=0.3):
    d = int(time_s * SR); y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += fb * y[s - d:e - d]
    return (1 - mix) * x + mix * fft_filter(y, hi=5000)

def soft_clip(x, drive=1.0): return np.tanh(x * drive) / np.tanh(drive)

def norm(x, peak=0.9): return (x / (np.max(np.abs(x)) + 1e-9) * peak).astype(np.float32)

def write_wav(path, x, sr=SR):
    import wave
    x = np.clip(x, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())

def read_wav(path):
    import wave
    with wave.open(path) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
