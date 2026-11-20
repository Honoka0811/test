"""Synthesizes the whole soundtrack (drone, UI sounds, rattle, bang, sting) -> audio.wav"""
import json, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, "timeline.json")))
SR = 44100
N = int(TL["end"] * SR)
rng = np.random.default_rng(13)
mix = np.zeros((N, 2))
T = np.arange(N) / SR

def bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))

def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N: return
    sig = sig[: N - i]
    mix[i:i + len(sig), 0] += sig * gain * (1 - max(0, pan))
    mix[i:i + len(sig), 1] += sig * gain * (1 + min(0, pan))

def env(n, a=0.005, d=None):
    e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    if d: e *= np.exp(-np.arange(n) / SR / d)
    return e

def seg(t0, t1): return np.arange(int((t1 - t0) * SR)) / SR
def fade(x, a=0.01, r=0.01):
    na, nr = int(a * SR), int(r * SR); x = x.copy()
    x[:na] *= np.linspace(0, 1, na); x[-nr:] *= np.linspace(1, 0, nr); return x

def blip(f0, f1, dur, d):
    t = seg(0, dur); f = np.linspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.003, d)

def tick(lo=2000, hi=7000, dur=0.02, d=0.004):
    n = int(dur * SR); return bp(rng.standard_normal(n), lo, hi) * env(n, 0.0005, d)

def thud(f=52, dur=1.6, d=0.25, noise=0.6):
    t = seg(0, dur)
    body = np.sin(2 * np.pi * (f * t + 30 * (1 - np.exp(-t * 30)) / 30)) * np.exp(-t / d)
    nz = bp(rng.standard_normal(len(t)), 40, 900) * np.exp(-t / 0.07) * noise
    return body + nz

recv = np.concatenate([blip(1175, 1175, 0.07, 0.03), blip(1568, 1568, 0.16, 0.05)])
sent = blip(520, 880, 0.09, 0.035)

# --- hook: sub boom + reversed swell into the cut
add(thud(45, 2.0, 0.5, 0.3), 0.05, 0.9)
t = seg(0, TL["hookEnd"]); sw = bp(rng.standard_normal(len(t)), 300, 5000) * (t / t[-1]) ** 4
add(fade(sw, 0.01, 0.004), 0, 0.12)

# --- drone A: uneasy room tone until the reveal, then hard cut
t0, t1 = TL["hookEnd"], TL["silence"][0]
t = seg(t0, t1)
dr = sum(np.sin(2 * np.pi * f * t + p) * a for f, p, a in [(49, 0, .5), (51.3, 1, .4), (98.6, 2, .18), (147.5, .5, .07)])
dr *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.13 * t)
dr += bp(rng.standard_normal(len(t)), 120, 600) * 0.05
add(fade(dr * np.minimum(1, t / 1.5), 0.01, 0.008), t0, 0.33)

# --- silence: only a thin ear-ringing tone
t = seg(*TL["silence"]); add(fade(np.sin(2 * np.pi * 6200 * t) * (t / t[-1]), 0.01, 0.3), TL["silence"][0], 0.012)

# --- tension B: rising dissonant cluster + sub + accelerating heartbeat up to the bang
t0, t1 = TL["silence"][1], TL["bang"]
t = seg(t0, t1); k = t / t[-1]
gl = 1 + 0.18 * k ** 2
cl = sum(np.sin(2 * np.pi * np.cumsum(f * gl) / SR + i) * (0.7 + 0.3 * np.sin(2 * np.pi * (5 + i) * t)) for i, f in enumerate([622, 659, 932, 988, 1397]))
ten = cl * 0.05 * k ** 2.2 + np.sin(2 * np.pi * 41 * t) * 0.5 * k + bp(rng.standard_normal(len(t)), 2500, 9000) * 0.03 * k ** 3
add(fade(ten, 0.05, 0.004), t0, 0.5)
hb = t0 + 0.3; iv = 0.95
while hb < t1 - 0.4:
    g = 0.35 + 0.5 * (hb - t0) / (t1 - t0)
    add(thud(58, 0.4, 0.07, 0.15), hb, g); add(thud(50, 0.4, 0.06, 0.1), hb + iv * 0.28, g * 0.7)
    hb += iv; iv = max(0.46, iv * 0.93)

# --- door knob rattle
t = TL["rattle"][0]
while t < TL["rattle"][1]:
    ph = (t - TL["rattle"][0]) % 0.75
    if ph < 0.5:
        ring = blip(1900 + rng.uniform(-200, 300), 1700, 0.09, 0.02) * 0.4
        c = tick(1200, 6000, 0.09, 0.012); c[:len(ring)] += ring[:len(c)]
        add(c, t, rng.uniform(0.35, 0.8), pan=0.35)
    t += rng.uniform(0.05, 0.11)

# --- bang on the door, then dead air
b = thud(48, 2.2, 0.35, 1.0); add(b, TL["bang"], 1.6)
add(thud(70, 0.8, 0.12, 0.8), TL["bang"] + 0.012, 0.8, pan=0.3)

# --- drone C: something else is holding the phone
t0, t1 = TL["possessed"], TL["glitch"][0]
t = seg(t0, t1); k = t / t[-1]
gr = (np.sin(2 * np.pi * 36 * t) + np.sin(2 * np.pi * 38.2 * t) + 0.4 * np.sign(np.sin(2 * np.pi * 72.5 * t)) * 0.3)
gr = gr * (0.25 + 0.75 * k) + bp(rng.standard_normal(len(t)), 150, 2500) * 0.25 * k ** 3
br = bp(rng.standard_normal(len(t)), 300, 1400) * np.clip(np.sin(2 * np.pi * 0.31 * t - 1), 0, 1) ** 2 * 0.35  # breathing
add(fade(gr * 0.3 + br, 0.4, 0.004), t0, 0.6)

# --- glitch burst
t = seg(*TL["glitch"]); n = len(t)
sh = np.repeat(rng.uniform(-1, 1, n // 40 + 1), 40)[:n]
gate = np.repeat(rng.uniform(0, 1, n // 1500 + 1) > 0.3, 1500)[:n]
add(fade((sh * 0.6 + np.sign(np.sin(2 * np.pi * 110 * t * (1 + 6 * t))) * 0.4) * gate, 0.002, 0.002), TL["glitch"][0], 0.55)
for m in (TL["possessed"], 34.6, 37.2):
    add(fade(np.repeat(rng.uniform(-1, 1, 200), 22)[:int(0.1 * SR)], 0.002, 0.002), m, 0.3)

# --- face flash: breathy shriek inside the black
t = seg(0, 0.26); add(fade(bp(rng.standard_normal(len(t)), 1800, 7000) * np.linspace(.3, 1, len(t)), 0.01, 0.004), TL["black"][0] + 0.17, 0.5)

# --- final sting
t = seg(TL["final"], TL["cut"])
saw = lambda f: 2 * ((f * t) % 1) - 1
st = sum(saw(f) for f in (110, 116.5, 155.6, 311.1, 329.6, 466.2, 493.9)) * 0.1
st = bp(st, 60, 5000) * np.exp(-t / 1.4)
sc = bp(rng.standard_normal(len(t)), 900, 4500) * np.exp(-t / 0.5) * 0.5
add(fade(st + sc, 0.002, 0.006), TL["final"], 1.3)
add(thud(40, 2.0, 0.6, 0.8), TL["final"], 1.5)

# --- UI sounds
for it in TL["items"]:
    if it.get("instant"): continue
    if it["side"] == "y":
        add(recv, it["t"], 0.3)
    else:
        add(sent, it["t"], 0.22)
        n = len(it["text"]); slow = it.get("slow")
        d = slow or min(1.3, 0.3 + n * 0.055); s = it["t"] - d - 0.12
        for i in range(n):
            if it["text"][i] == " ": continue
            tt = s + d * i / n + (0 if slow else rng.uniform(-0.01, 0.01))
            if slow: add(tick(500, 2500, 0.12, 0.03), tt, 0.9)   # heavy, deliberate taps
            else: add(tick(), tt, 0.35)

# --- light room reverb, limiter, hard cut to silence
ir_n = int(1.2 * SR); ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.3); ir /= np.sqrt((ir ** 2).sum())
L = N + ir_n
for c in range(2):
    wet = np.fft.irfft(np.fft.rfft(mix[:, c], L) * np.fft.rfft(np.roll(ir, c * 37), L), L)[:N]
    mix[:, c] += wet * 0.22
cut = int(TL["cut"] * SR); mix[cut:] = 0
s0, s1 = int((TL["black"][0]) * SR), int((TL["black"][0] + 0.17) * SR); mix[s0:s1] *= 0.05
mix /= np.abs(mix).max() / 1.6
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
