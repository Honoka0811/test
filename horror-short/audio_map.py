"""Soundtrack for the location-sharing short (all synthesized) -> audio.wav"""
import json, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.environ.get("TIMELINE") or os.path.join(HERE, "map.json")))
SR = 44100
N = int(TL["end"] * SR)
rng = np.random.default_rng(21)
mix = np.zeros((N, 2))

def bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))
def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i]
    mix[i:i + len(sig), 0] += sig * gain * (1 - max(0, pan))
    mix[i:i + len(sig), 1] += sig * gain * (1 + min(0, pan))
def seg(t0, t1): return np.arange(int((t1 - t0) * SR)) / SR
def fade(x, a=0.01, r=0.01):
    na, nr = max(1, int(a * SR)), max(1, int(r * SR)); x = x.copy()
    x[:na] *= np.linspace(0, 1, na); x[-nr:] *= np.linspace(1, 0, nr); return x
def noise(n): return rng.standard_normal(n)
def thud(f=52, dur=1.6, d=0.25, nz=0.6):
    t = seg(0, dur)
    return np.sin(2 * np.pi * f * t) * np.exp(-t / d) + bp(noise(len(t)), 40, 900) * np.exp(-t / 0.07) * nz
def ding(f=1175, rate=1.0, d=0.35):          # notification: two soft bell partials
    t = seg(0, 1.2 / rate)
    return (np.sin(2 * np.pi * f * rate * t) + 0.5 * np.sin(2 * np.pi * f * rate * 1.5 * t) + 0.25 * np.sin(2 * np.pi * f * rate * 2.76 * t)) * np.exp(-t * rate / d) * np.minimum(1, t / 0.004)
def ping(f):                                  # location update
    t = seg(0, 0.5); return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.09) * np.minimum(1, t / 0.003)

HOOK, ON, MV, ARR, JS, FIN, CUT = TL["hookEnd"], TL["online"], TL["moveStart"], TL["arrive"], TL["joinStart"], TL["final"], TL["cut"]

# hook
add(thud(45, 2.0, 0.5, 0.3), 0.05, 0.9)
t = seg(0, HOOK); add(fade(bp(noise(len(t)), 300, 5000) * (t / t[-1]) ** 4, 0.01, 0.004), 0, 0.12)

# night room tone until she arrives
t = seg(HOOK, ARR)
add(fade(bp(noise(len(t)), 60, 400), 0.8, 0.01), HOOK, 0.035)
add(fade(np.sin(2 * np.pi * 50 * t) * 0.6 + np.sin(2 * np.pi * 100.3 * t) * 0.2, 0.8, 0.01), HOOK, 0.03)

# banners
add(ding(), ON, 0.4); add(ding(), MV, 0.35); add(ding(1397), TL["near"], 0.45)

# she moves: a ping per location update, climbing; drone and heartbeat grow with her progress
for jt, fr in TL["mjumps"]:
    add(ping(660 + 700 * fr), jt, 0.16 + 0.3 * fr)
    add(thud(55, 0.35, 0.06, 0.1), jt + 0.02, 0.25 + 0.75 * fr)
t = seg(MV, ARR); k = t / t[-1]
dr = (np.sin(2 * np.pi * 46 * t) + np.sin(2 * np.pi * 48.6 * t)) * k ** 1.5 * 0.5
cl = sum(np.sin(2 * np.pi * f * t * (1 + 0.1 * k) + i) for i, f in enumerate((740, 784, 1109, 1175))) * 0.045 * k ** 3
add(fade(dr + cl, 0.5, 0.004), MV, 0.8)

# 0 m: everything stops. she is in the room.
add(ding(880, 0.5, 0.22), ARR, 0.5)
t = seg(ARR + 0.6, JS); add(fade(bp(noise(len(t)), 50, 250), 0.4, 0.05), ARR + 0.6, 0.05)
for j in range(4):
    x = seg(0, 0.09); f0 = rng.uniform(210, 360)
    add(bp(np.sign(np.sin(2 * np.pi * f0 * x * (1 + 2 * x))) * np.exp(-x / 0.035), 180, 2200), ARR + 1.5 + j * 0.13, 0.35, pan=0.6)

# then the rest of them come online: dings piling into a mass, and a swarm drone
J = TL["joins"]; scale = [1175, 1109, 1245, 988, 1319, 932, 1397, 880, 1480, 831]
for i, j in enumerate(J):
    g = 0.42 if i < 4 else max(0.1, 0.34 - 0.004 * i)
    add(ding(scale[i % len(scale)] * (1 if i < 4 else rng.uniform(0.94, 1.06)), 1.0, 0.3 if i < 4 else 0.18), j["t"], g, pan=rng.uniform(-.6, .6) if i >= 4 else 0)
t = seg(JS, FIN); k = t / t[-1]
sw = (np.sin(2 * np.pi * 41 * t) + np.sin(2 * np.pi * 43.7 * t)) * k ** 1.3 * 0.6
sw += sum(np.sin(2 * np.pi * f * t * (1 + 0.16 * k ** 2) + i) for i, f in enumerate((622, 659, 932, 988, 1397, 1480))) * 0.05 * k ** 2.5
sw += bp(noise(len(t)), 200, 5000) * 0.25 * k ** 4
st = JS + 4.0; iv = 0.5                        # footfalls of many, getting denser
while st < FIN:
    add(thud(60, 0.3, 0.05, 0.3), st, 0.2 + 0.6 * (st - JS) / (FIN - JS), pan=rng.uniform(-.7, .7)); st += iv * rng.uniform(0.6, 1.2); iv = max(0.05, iv * 0.955)
add(fade(sw, 0.5, 0.003), JS, 0.95)

# final: dead silence, then one wrong notification
add(ding(1175, 0.42, 0.22), FIN + 0.25, 0.6)
add(thud(38, 2.4, 0.45, 0.2), FIN + 0.25, 0.5)
t = seg(FIN + 0.25, CUT); add(fade(np.sin(2 * np.pi * 36 * t) * (t / t[-1]), 0.1, 0.004), FIN + 0.25, 0.14)

# light room reverb, limiter, hard cut
ir_n = int(1.0 * SR); ir = noise(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.25); ir /= np.sqrt((ir ** 2).sum())
L = N + ir_n
for c in range(2):
    mix[:, c] += np.fft.irfft(np.fft.rfft(mix[:, c], L) * np.fft.rfft(np.roll(ir, c * 37), L), L)[:N] * 0.18
a, b = int(FIN * SR), int((FIN + 0.25) * SR); mix[a:b] = 0
mix[int(CUT * SR):] = 0
mix /= np.abs(mix).max() / 1.6
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
