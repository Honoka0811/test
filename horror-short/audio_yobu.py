"""Soundtrack for the 'called only once' folk-tale short (all synthesized) -> audio.wav
Wind, a hearth, knocks on a wooden door, a plucked string, a drum. No sine tones or synthetic voices."""
import json, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.environ.get("TIMELINE") or os.path.join(HERE, "yobu.json")))
SR = 44100
N = int(TL["end"] * SR)
rng = np.random.default_rng(29)
mix = np.zeros((N, 2))

def bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))
def seg(t0, t1): return np.arange(int((t1 - t0) * SR)) / SR
def noise(n): return rng.standard_normal(n)
def fade(x, a=0.01, r=0.01):
    na, nr = max(1, int(a * SR)), max(1, int(r * SR)); x = x.copy()
    x[:na] *= np.linspace(0, 1, na); x[-nr:] *= np.linspace(1, 0, nr); return x
def put(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i]
    mix[i:i + len(sig), 0] += sig * gain * (1 - max(0, pan)); mix[i:i + len(sig), 1] += sig * gain * (1 + min(0, pan))
def reverb(x, tau, wet):
    n = int(tau * 5 * SR); ir = noise(n) * np.exp(-np.arange(n) / SR / tau); ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n; return np.concatenate([x, np.zeros(n)]) + np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L) * wet

def don(g=1.0):
    t = seg(0, 0.9); return (np.sin(2 * np.pi * (62 * t + 40 * (1 - np.exp(-t * 28)) / 28)) * np.exp(-t / 0.2) + bp(noise(len(t)), 80, 1400) * np.exp(-t / 0.03) * 0.9) * g
def knock(hard=1.0):            # knuckles on a wooden door: board resonance + contact noise
    t = seg(0, 0.5)
    x = np.sin(2 * np.pi * 172 * t) * np.exp(-t / 0.05) + 0.6 * np.sin(2 * np.pi * 395 * t) * np.exp(-t / 0.022) + 0.3 * np.sin(2 * np.pi * 88 * t) * np.exp(-t / 0.09)
    x += bp(noise(len(t)), 700, 3800) * np.exp(-t / 0.006) * 0.8 * hard
    return reverb(x, 0.22, 0.35)
def pluck(f, dur=3.0):
    n = max(2, int(round(SR / f))); buf = bp(np.tile(rng.uniform(-1, 1, n), 4), 80, 5000)[:n]; out = np.empty(int(dur * SR))
    for i in range(len(out)):
        j = i % n; out[i] = buf[j]; buf[j] = 0.996 * 0.5 * (buf[j] + buf[(j + 1) % n])
    return reverb(out * np.minimum(1, np.arange(len(out)) / 60), 0.35, 0.25) * 1.7
def wind(t0, t1, g, lo=120, hi=900, gust=0.11):
    t = seg(t0, t1); l = 0.55 + 0.45 * np.sin(2 * np.pi * gust * t + rng.uniform(0, 6)) * np.sin(2 * np.pi * gust * 0.43 * t + 1)
    put(fade(bp(noise(len(t)), lo, hi) * l, 0.6, 0.6), t0, g * 2.4, pan=0.15)
def hearth(t0, t1, g):          # low burning + crackles
    t = seg(t0, t1); x = bp(noise(len(t)), 150, 700) * 0.25
    for _ in range(int((t1 - t0) * 7)):
        i = int(rng.uniform(0, len(t) - 3000)); c = seg(0, 0.03); x[i:i + len(c)] += bp(noise(len(c)), 1500, 7000) * np.exp(-c / rng.uniform(0.002, 0.008)) * rng.uniform(0.3, 1.2)
    put(fade(x, 0.5, 0.4), t0, g * 2.8, pan=-0.45)
def creak(dur, f0=38):          # wood and paper under strain: slow stick-slip, made of noise bursts
    t = seg(0, dur); rate = f0 * (0.6 + 0.8 * t / dur); ph = np.cumsum(rate) / SR
    am = np.clip(np.sin(2 * np.pi * ph), 0, 1) ** 6
    return bp(noise(len(t)), 300, 2600) * am * np.sin(np.pi * t / dur) ** 0.6
def heartbeat(t0, t1, g0, g1):
    hb = t0; iv = 1.0
    while hb < t1:
        g = g0 + (g1 - g0) * (hb - t0) / (t1 - t0)
        put(don(0.5), hb, g * 0.9); put(don(0.4), hb + iv * 0.27, g * 0.62); hb += iv; iv = max(0.55, iv * 0.95)

SC = [(s["k"], s["t"]) for s in TL["scenes"]] + [("end", TL["cut"])]
D3, A3, D4, Eb4, G4, A4, Bb4 = 146.8, 220.0, 293.7, 311.1, 392.0, 440.0, 466.2
DUCK = []                                                                # (from, to, level): when it speaks, the world goes quiet
put(don(), 0.1, 0.6); put(pluck(D3), 2.0, 0.6)                          # hook
for (k, t0), (_, t1) in zip(SC[:-1], SC[1:]):
    if k == "house":
        wind(t0, t1 + 0.3, 0.16); wind(t0, t1 + 0.3, 0.05, 900, 3500, 0.23)
        for i, f in enumerate((D4, Eb4, D4, A3)):
            if t0 + 0.4 + i * 1.3 < t1 - 0.4: put(pluck(f), t0 + 0.4 + i * 1.3, 0.7, pan=rng.uniform(-.2, .2))
    elif k == "shoji1":
        hearth(t0, t1, 0.22); wind(t0, t1, 0.06)
    elif k == "snow":
        wind(t0, t1, 0.07)
        for i, f in enumerate((A4, G4, Eb4, D3, Eb4, D3)):
            if t0 + 0.5 + i * 2.0 < t1 - 0.5: put(pluck(f), t0 + 0.5 + i * 2.0, 0.6)
    elif k == "black":
        put(pluck(A3), t0 + 0.3, 0.5); put(pluck(D3), t0 + 3.2, 0.5)
    elif k == "phone":
        t = seg(t0, t1); put(fade(bp(noise(len(t)), 60, 260) * 0.5, 0.3, 0.05), t0, 0.05)        # a quiet room at night
ends = {k: t1 for (k, t0), (_, t1) in zip(SC[:-1], SC[1:])}

c0, c1 = TL["call1"]                                                     # 'moshi' - once
DUCK.append((c0 - 0.15, c0 + 2.0, 0.04))
heartbeat(c0 + 2.6, ends["shoji1"] - 0.3, 0.25, 0.75)
put(don(0.9), TL["reveal"] + 2.1, 0.6)                                   # dead since the first night
put(don(), TL["taken"], 0.75)                                            # he answered it

put(don(0.8), TL["rule"], 0.5)
R0, AN = TL["ring"], TL["answer"]                                        # the phone vibrating on the floor
tt = R0 + 0.3
while tt < AN - 0.2:
    d = min(1.0, AN - 0.2 - tt); x = seg(0, d)
    v = (bp(noise(len(x)), 90, 420) * 0.8 + bp(np.sign(np.sin(2 * np.pi * 152 * x)), 120, 900) * 0.25) * (0.6 + 0.4 * (np.sin(2 * np.pi * 37 * x) > 0))
    put(fade(v, 0.02, 0.04), tt, 0.45); tt += 1.6
x = seg(0, 0.06); put(bp(noise(len(x)), 800, 5000) * np.exp(-x / 0.01), AN, 0.3)         # tap to answer
t = seg(AN, TL["cut"]); put(fade(bp(noise(len(t)), 300, 3400) * 0.5, 0.05, 0.02), AN, 0.06)  # an open line, hissing
DUCK.append((TL["call2"][0] - 0.1, TL["cut"], 0.12))                     # after 'moshi', nothing but the line
x = seg(0, 3.0)
for a0, a1, lv in DUCK:
    i0, i1, r = int(a0 * SR), int(a1 * SR), int(0.12 * SR)
    env = np.full(i1 - i0, lv); env[:r] = np.linspace(1, lv, r)
    if a1 < TL["cut"] - 0.1: env[-r:] = np.linspace(lv, 1, r)
    mix[i0:i1] *= env[:, None]
put(don(), TL["dead"], 0.8); put(np.sin(2 * np.pi * 34 * x) * np.exp(-x / 1.0), TL["dead"], 0.8)   # lands inside the silence

mix[int(TL["cut"] * SR):] = 0
mix /= np.abs(mix).max() / 1.4
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
