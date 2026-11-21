"""Soundtrack for the folk-tale short (all synthesized) -> audio.wav
koto-like plucks in a miyako-bushi scale, evening cicadas, wind, a temple bell,
and a formant-synthesised call from the mountain that is deliberately not quite a human voice."""
import json, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.environ.get("TIMELINE") or os.path.join(HERE, "kami.json")))
SR = 44100
N = int(TL["end"] * SR)
rng = np.random.default_rng(11)
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
def reverb(x, tau, wet):
    n = int(tau * 5 * SR); ir = noise(n) * np.exp(-np.arange(n) / SR / tau); ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n; return np.concatenate([x, np.zeros(n)]) + np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L) * wet
def thud(f=52, dur=1.6, d=0.25, nz=0.6):
    t = seg(0, dur)
    return np.sin(2 * np.pi * f * t) * np.exp(-t / d) + bp(noise(len(t)), 40, 900) * np.exp(-t / 0.07) * nz

def pluck(f, dur=3.0, damp=0.996):          # Karplus-Strong string
    n = int(SR / f); buf = rng.uniform(-1, 1, n); buf = bp(np.tile(buf, 4), 80, 5000)[:n]
    out = np.empty(int(dur * SR))
    for i in range(len(out)):
        j = i % n; out[i] = buf[j]; buf[j] = damp * 0.5 * (buf[j] + buf[(j + 1) % n])
    return out * np.minimum(1, np.arange(len(out)) / 60)
def bell():
    t = seg(0, 7.0); x = np.zeros(len(t))
    for r, a, d in [(1, 1, 3.2), (2.02, 0.6, 2.2), (2.41, 0.5, 1.6), (3.0, 0.35, 1.2), (4.13, 0.25, 0.8), (5.4, 0.15, 0.5)]:
        x += a * np.sin(2 * np.pi * 98 * r * t) * np.exp(-t / d) * (1 + 0.25 * np.sin(2 * np.pi * (0.7 + r * 0.13) * t))
    return x + bp(noise(len(t)), 200, 2500) * np.exp(-t / 0.03) * 0.8
def cicada():                               # evening cicada: a falling, slowing "kana-kana-kana"
    t = seg(0, 3.4); k = t / t[-1]
    rate = 11 - 6 * k; ph = np.cumsum(rate) / SR
    am = np.clip(np.sin(2 * np.pi * ph), 0, 1) ** 0.6
    car = np.sin(2 * np.pi * np.cumsum(3900 - 500 * k) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(5850 - 700 * k) / SR)
    return car * am * np.sin(np.pi * k) ** 0.7
def gravel():
    t = seg(0, 0.4); x = bp(noise(len(t)), 900, 6000) * (np.exp(-t / 0.05) + 0.6 * np.exp(-((t - 0.16) / 0.04) ** 2))
    return x + np.sin(2 * np.pi * 60 * t) * np.exp(-t / 0.06) * 1.2

V = {"o": (500, 900), "u": (380, 1300), "i": (320, 2700), "a": (950, 1500)}
def call(pitch=1.0, slow=1.0):
    """'mo-u-i-i-ka-i' as vowels only, sung on the children's-game interval, by something imitating a child."""
    parts = [(0.75, 392, 392, "o", "u"), (0.65, 392, 392, "i", "i"), (0.07, 0, 0, None, None), (0.4, 440, 440, "a", "a"), (1.3, 440, 330, "a", "i")]
    f0 = []; F1 = []; F2 = []; amp = []
    for d, a, b, va, vb in parts:
        n = int(d * slow * SR); u = np.linspace(0, 1, n)
        if va is None: f0 += [392] * n; F1 += [F1[-1]] * n; F2 += [F2[-1]] * n; amp += [0] * n; continue
        g = np.clip(u * 3.5, 0, 1)
        f0 += list((a + (b - a) * np.clip(u * 2.2, 0, 1)) * pitch); F1 += list(V[va][0] + (V[vb][0] - V[va][0]) * g); F2 += list(V[va][1] + (V[vb][1] - V[va][1]) * g)
        amp += list(np.minimum(1, u * n / (0.05 * SR)) * np.minimum(1, (1 - u) * n / (0.09 * SR)))
    f0 = np.array(f0); F1 = np.array(F1); F2 = np.array(F2); amp = np.array(amp); n = len(f0); t = np.arange(n) / SR
    f0 = f0 * (1 + 0.012 * np.sin(2 * np.pi * 5.3 * t) + 0.004 * np.cumsum(noise(n)) / np.sqrt(np.arange(1, n + 1)))
    src = (2 * ((np.cumsum(f0) / SR) % 1) - 1) * amp + noise(n) * 0.06 * amp
    W, H = 1024, 256; win = np.hanning(W); out = np.zeros(n + W); fr = np.fft.rfftfreq(W, 1 / SR)
    pad = np.concatenate([src, np.zeros(W)])
    for s0 in range(0, n, H):
        c = min(n - 1, s0 + W // 2)
        env = sum(a / (1 + ((fr - F) / bw) ** 2) for F, bw, a in [(F1[c], 90, 1.0), (F2[c], 120, 0.7), (3100, 180, 0.25)])
        out[s0:s0 + W] += np.fft.irfft(np.fft.rfft(pad[s0:s0 + W] * win) * env, W) * win
    out = out[:n] / (np.abs(out).max() + 1e-9)
    tail = int(0.5 * SR); out[-tail:] *= np.linspace(1, 0, tail) ** 1.5
    return out

SC = {s["k"]: s["t"] for s in TL["scenes"]}
D3, A3, D4, Eb4, G4, A4, Bb4, D5 = 146.8, 220.0, 293.7, 311.1, 392.0, 440.0, 466.2, 587.3

# hook: temple bell out of the dark
add(bell(), 0.15, 0.55)

# koto
for tt, f, g in [(2.9, D4, 1), (3.5, Eb4, .8), (4.1, D4, .8), (5.0, A3, 1), (6.2, G4, .9), (6.8, A4, .9), (7.4, Bb4, 1), (8.0, A4, .8), (8.9, D4, 1),
                 (9.9, D5, 1), (10.5, Bb4, .8), (11.1, A4, .8), (11.7, G4, .8), (12.6, A4, .9), (13.2, Eb4, .9), (13.8, D4, 1), (14.9, A3, 1), (15.5, D3, 1.1),
                 (34.9, D3, 1), (36.3, Eb4, .7), (37.7, D4, .8), (39.4, A3, .9), (40.7, Eb4, .5)]:
    add(reverb(pluck(f), 0.35, 0.25), tt, 1.0 * g, pan=rng.uniform(-.25, .25))

# evening cicadas over the village and the shrine
for tt, p in [(3.1, -0.5), (6.8, 0.5), (10.4, -0.3), (13.6, 0.4)]:
    add(reverb(cicada(), 0.4, 0.5), tt, 0.17, pan=p)

# wind
t = seg(SC["village"], SC["black"] + 5); lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t) * np.sin(2 * np.pi * 0.047 * t + 1)
add(fade(bp(noise(len(t)), 120, 900) * lfo, 1.0, 1.5), SC["village"], 0.11)
for k in ("village", "shrine", "under"): add(thud(55, 1.2, 0.25, 0.3), SC[k], 0.45)

# under the floor: the game, then the other voice
for tt in (16.5, 17.9):
    x = seg(0, 0.2); add((np.sin(2 * np.pi * 620 * x) + 0.5 * np.sin(2 * np.pi * 1480 * x)) * np.exp(-x / 0.03), tt, 0.1)
far = reverb(bp(call(1.0, 1.0), 200, 2400), 0.8, 1.6)
add(far, TL["call1"], 0.3, pan=0.35)

# it gets dark; something answers the answer
D0, L0, L1 = TL["dim"], TL["legs"][0], TL["legs"][1]
t = seg(D0, L1); k = t / t[-1]
dr = (np.sin(2 * np.pi * 43 * t) + np.sin(2 * np.pi * 45.6 * t)) * (0.2 + 0.8 * k) * 0.5
dr += sum(np.sin(2 * np.pi * f * t * (1 + 0.05 * k) + i) for i, f in enumerate((587, 622, 880, 932))) * 0.04 * k ** 2
add(fade(dr, 1.0, 0.004), D0, 0.85)
hb = D0 + 1.2; iv = 1.0
while hb < L1 - 0.3:
    g = 0.25 + 0.5 * (hb - D0) / (L1 - D0)
    add(thud(58, 0.4, 0.07, 0.15), hb, g); add(thud(50, 0.4, 0.06, 0.1), hb + iv * 0.28, g * 0.7); hb += iv; iv = max(0.5, iv * 0.94)
for i, st in enumerate(TL["steps"]):
    add(reverb(gravel(), 0.2, 0.2), st, 0.5, pan=0.6 - 0.24 * i)

# the sandals: bell, then the old woman's warning in near silence
add(bell(), SC["geta"] + 0.1, 0.5)

# and then it asks you
near = reverb(bp(call(0.9, 1.18), 150, 4500), 0.5, 0.5)
add(near, TL["call2"], 0.75)
add(thud(36, 3.0, 1.0, 0.4), TL["finalText"], 0.9)
t = seg(TL["finalText"], TL["cut"]); add(fade(sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate((1245, 1319, 1865))) * (t / t[-1]) ** 2, 0.1, 0.003), TL["finalText"], 0.05)

a, b = int((SC["black"] + 4.9) * SR), int(TL["call2"] * SR); mix[a:b] *= 0.0      # dead air before it speaks
mix[int(TL["cut"] * SR):] = 0
mix /= np.abs(mix).max() / 1.3
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
