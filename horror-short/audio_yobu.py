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

SC = [(s["k"], s["t"]) for s in TL["scenes"]]
D3, A3, D4, Eb4, G4, A4, Bb4 = 146.8, 220.0, 293.7, 311.1, 392.0, 440.0, 466.2

put(don(), 0.1, 1.0)                                                    # hook
wind(3.0, 9.9, 0.16); wind(3.0, 9.9, 0.05, 900, 3500, 0.23)             # outside, in the snow
for tt, f in [(3.4, D4), (4.3, Eb4), (5.4, D4), (6.7, A3), (7.6, Bb4), (8.4, A4)]: put(pluck(f), tt, 0.7, pan=rng.uniform(-.2, .2))

hearth(9.6, 24.0, 0.22); wind(9.6, 24.0, 0.05)                           # first night, indoors
put(knock(), TL["knock1"], 1.3, pan=-0.3)
heartbeat(14.0, 23.6, 0.25, 0.7)
put(pluck(D3), 20.9, 0.6)

wind(24.0, 31.0, 0.07)                                                   # morning
for tt, f in [(24.5, A4), (25.6, G4), (27.9, Eb4), (29.4, D3)]: put(pluck(f), tt, 0.6)
put(don(0.8), 27.8, 0.7)

hearth(31.0, 47.0, 0.22); wind(31.0, 47.0, 0.06)                         # second night: it has learned
for kt in TL["knock2"]: put(knock(), kt, 1.3, pan=-0.3)
heartbeat(35.0, 44.2, 0.3, 0.9)
put(creak(0.9, 30), TL["arm"][0] + 0.1, 0.3, pan=0.5)                    # mother shifts her weight
S0, S1 = TL["stretch"]
put(creak(S1 - S0, 34), S0, 0.9, pan=-0.3); put(creak(S1 - S0 - 0.4, 51), S0 + 0.4, 0.5, pan=-0.2)
t = seg(S0, S1); k = t / t[-1]
put(fade(bp(noise(len(t)), 40, 160) * k ** 1.5 * 3 + (np.sin(2 * np.pi * 40 * t) + np.sin(2 * np.pi * 42.7 * t)) * k * 0.5, 0.2, 0.004), S0, 1.0)
put(don(), S0, 1.0)

put(pluck(A3), 47.4, 0.5); put(pluck(D3), 48.8, 0.5)                     # grandmother's warning, nearly silent

hearth(51.0, TL["cut"], 0.16)                                            # tonight
t = seg(TL["poke"], TL["hole"]); put(fade(bp(noise(len(t)), 1500, 6000) * (0.4 + 0.6 * t / t[-1]), 0.05, 0.01), TL["poke"], 0.12, pan=-0.3)
x = seg(0, 0.12); put(bp(noise(len(x)), 1200, 8000) * np.exp(-x / 0.02), TL["hole"], 0.7, pan=-0.3)    # the paper gives
put(don(), TL["lastText"], 1.1)
kt = TL["lastText"] + 0.5; iv = 0.42; g = 0.8                            # ...and now it calls as many times as it likes
while kt < TL["cut"]:
    put(knock(1.2), kt, g, pan=-0.3); kt += iv; iv = max(0.11, iv * 0.86); g = min(1.6, g * 1.07)

mix[int(TL["cut"] * SR):] = 0
mix /= np.abs(mix).max() / 1.4
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
