# -*- coding: utf-8 -*-
"""ダーク系BGMを numpy だけで合成する(外部音源なし・権利フリー)。
Cマイナー / 66BPM。低音ドローン + 不穏な弦パッド + オルゴール風メロディ + 心音キック + 各順位の切り替わりに衝撃音。
generate(total, hits) -> mono float32 (48kHz)
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 66
BEAT = 60 / BPM
BAR = BEAT * 4
PROG = [[48, 51, 55], [44, 48, 51], [41, 44, 48], [43, 47, 50]]   # Cm  Ab  Fm  G
MELO = [72, 75, 74, 71, 72, 67, 68, 67,  72, 75, 79, 78, 77, 75, 74, 71]  # オルゴール 8分音符×16 (2小節)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, t0, sig):
    s = int(t0 * SR); e = min(s + len(sig), len(buf))
    if e > s > -1: buf[s:e] += sig[:e - s]

def pad(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, np.float32)
    for det in (-0.006, 0.0, 0.006):
        ph = rng.uniform(0, 6.28)
        for h in range(1, 9):
            sig += (1 / h ** 1.4) * np.sin(2 * np.pi * f * h * (1 + det) * t + ph * h)
    env = np.minimum(1, np.minimum(t / 1.2, (dur - t) / 1.2)).clip(0)
    trem = 1 + 0.15 * np.sin(2 * np.pi * 4.5 * t)
    return sig * env * trem

def bell(f, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2*np.pi*f*t) + 0.45*np.sin(2*np.pi*f*2.76*t)*np.exp(-t/0.25) + 0.25*np.sin(2*np.pi*f*5.4*t)*np.exp(-t/0.08))
    return (s * np.exp(-t / 0.7) * np.minimum(1, t / 0.002)).astype(np.float32)

def thump(f0=70, dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 38 + (f0 - 38) * np.exp(-t / 0.05)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)).astype(np.float32)

def impact(rng, dur=3.5):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 30 + 90 * np.exp(-t / 0.15)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    noise = rng.standard_normal(n).astype(np.float32)
    noise = np.convolve(noise, np.ones(40) / 40, 'same') * np.exp(-t / 0.35)
    metal = sum(np.sin(2*np.pi*fr*t) for fr in (311, 467, 733, 1051)) * np.exp(-t / 0.6) * 0.12
    return (boom + 0.8 * noise + metal).astype(np.float32)

def riser(dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    k = 1 + (60 * (1 - t / dur)).astype(int)
    cs = np.cumsum(np.concatenate([[0], noise]))
    idx = np.arange(n)
    lp = (cs[idx + 1] - cs[np.maximum(0, idx + 1 - k)]) / k
    return (lp * (t / dur) ** 2.5).astype(np.float32)

def reverb(x, rng):
    ir_n = int(2.4 * SR); t = np.arange(ir_n) / SR
    ir = rng.standard_normal(ir_n).astype(np.float32) * np.exp(-t / 0.6)
    ir = np.convolve(ir, np.ones(12) / 12, 'same'); ir /= np.sqrt(np.sum(ir ** 2))
    n = len(x) + ir_n; N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:len(x)].astype(np.float32)

def generate(total, hits=(), seed=7):
    rng = np.random.default_rng(seed)
    n = int(total * SR); t = np.arange(n) / SR
    drone = (np.sin(2*np.pi*midi(36)*t) + 0.5*np.sin(2*np.pi*midi(43)*t*1.001) + 0.3*np.sin(2*np.pi*midi(24)*t))
    drone *= 0.5 + 0.2 * np.sin(2 * np.pi * 0.05 * t)
    pads = np.zeros(n, np.float32); bells = np.zeros(n, np.float32); drums = np.zeros(n, np.float32)
    nb = int(total / BAR) + 1
    for b in range(nb):
        for note in PROG[b % 4]:
            add(pads, b * BAR, pad(midi(note), BAR + 1.2, rng) * 0.05)
        add(drums, b * BAR, thump() * 0.9); add(drums, b * BAR + 0.28, thump(60) * 0.6)
        add(drums, b * BAR + 2 * BEAT, thump() * 0.8); add(drums, b * BAR + 2 * BEAT + 0.28, thump(60) * 0.5)
        if b >= 1:  # オルゴールは2小節目から
            for i in range(8):
                note = MELO[(b % 2) * 8 + i]
                if rng.random() < 0.85:
                    add(bells, b * BAR + i * BEAT / 2, bell(midi(note)) * 0.13)
    fx = np.zeros(n, np.float32)
    for h in hits:
        add(fx, h, impact(rng) * 0.55)
        if h > 1.6: add(fx, h - 1.5, riser(1.5, rng) * 0.25)
    wet = reverb(pads + bells, rng)
    mix = 0.12 * drone + pads + bells * 0.6 + wet * 0.9 + drums * 0.35 + fx + reverb(fx, rng) * 0.4
    fade = np.minimum(1, np.minimum(t / 1.5, (total - t) / 2.5)).clip(0)
    mix = (mix * fade).astype(np.float32)
    return mix / (np.max(np.abs(mix)) or 1) * 0.9

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    x = generate(total, [3, 10])
    with wave.open(sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
