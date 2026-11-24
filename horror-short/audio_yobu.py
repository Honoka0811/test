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
put(don(), 0.1, 0.6)                                                    # hook
seen = {}
for (k, t0), (_, t1) in zip(SC[:-1], SC[1:]):
    n = seen.get(k, 0); seen[k] = n + 1
    if k == "house":
        wind(t0, t1 + 0.3, 0.16); wind(t0, t1 + 0.3, 0.05, 900, 3500, 0.23)
        for i, f in enumerate((D4, Eb4, D4, A3, Bb4, A4, D4)):
            if t0 + 0.4 + i * 1.35 < t1 - 0.5: put(pluck(f), t0 + 0.4 + i * 1.35, 0.7, pan=rng.uniform(-.2, .2))
    elif k.startswith("shoji"):
        hearth(t0, t1, 0.22 if k != "shoji3" else 0.16); wind(t0, t1, 0.05)
    elif k == "snow":
        wind(t0, t1, 0.07)
        for i, f in enumerate(((A4, G4, Eb4, D3), (D3, Eb4, D3, A3, Eb4, D3))[min(n, 1)]):
            if t0 + 0.5 + i * 2.2 < t1 - 0.5: put(pluck(f), t0 + 0.5 + i * 2.2, 0.6)
    elif k == "black":
        put(pluck(A3), t0 + 0.3, 0.5); put(pluck(D3), t0 + 2.4, 0.5)
ends = {k: t1 for (k, t0), (_, t1) in zip(SC[:-1], SC[1:])}

put(knock(), TL["knock1"], 0.8, pan=-0.3)                               # first night: once
heartbeat(TL["knock1"] + 2.2, ends["shoji1"] - 0.4, 0.25, 0.7)

for kt in TL["knock2"]: put(knock(), kt, 0.8, pan=-0.3)                 # second night: twice
G0, G1 = TL["glide"]
heartbeat(TL["knock2"][0] + 2.4, G0 - 0.6, 0.3, 0.9)
put(creak(0.9, 30), TL["arm"][0] + 0.1, 0.3, pan=0.5)                    # mother shifts her weight
a0, a1 = int((G0 - 0.5) * SR), int((TL["arm"][1]) * SR)                   # the room goes dead while it slides
ramp = int(0.4 * SR); mix[a0:a0 + ramp] *= np.linspace(1, 0.08, ramp)[:, None]; mix[a0 + ramp:a1] *= 0.08
t = seg(G0, G1); put(fade(bp(noise(len(t)), 200, 1100) * np.sin(np.pi * t / t[-1]) ** 0.7, 0.3, 0.2), G0, 0.12, pan=-0.2)   # paper whispering as it passes
put(don(), TL["arm"][1], 0.7)                                             # her hand comes away

put(don(0.9), TL["reveal"], 0.7)                                         # he had been dead since the first night

for kt in TL["knock3"]: put(knock(), kt, 0.8, pan=-0.3)                 # tonight: three times
heartbeat(TL["knock3"][-1] + 1.2, TL["lastText"], 0.3, 0.9)
put(creak(1.6, 26), TL["lastText"] + 0.3, 0.25, pan=-0.3)                # palms settle on the paper; it does not tear
put(don(), TL["lastText"], 0.7)
kt = TL["lastText"] + 0.5; iv = 0.5; g = 0.5                             # ...and it keeps calling
while kt < TL["cut"]:
    put(knock(1.2), kt, g, pan=-0.3); kt += iv; iv = max(0.11, iv * 0.88); g = min(1.0, g * 1.06)

mix[int(TL["cut"] * SR):] = 0
mix /= np.abs(mix).max() / 1.4
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
