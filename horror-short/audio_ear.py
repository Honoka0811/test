"""Soundtrack for the hearing-test short (all synthesized, headphone-oriented) -> audio.wav
Test tones are dry and hard-panned. Everything that is "not the test" is placed behind-right
with interaural delay + head shadow and gets room reverb, so it sounds like it is in your room."""
import json, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.environ.get("TIMELINE") or os.path.join(HERE, "ear.json")))
SR = 44100
N = int(TL["end"] * SR)
rng = np.random.default_rng(3)
dry = np.zeros((N, 2)); room = np.zeros((N, 2))

def bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))
def seg(t0, t1): return np.arange(int((t1 - t0) * SR)) / SR
def noise(n): return rng.standard_normal(n)
def put(buf, sig, t, ch):
    i = int(t * SR)
    if i >= N: return
    sig = sig[: N - i]; buf[i:i + len(sig), ch] += sig
def place(sig, t, az, gain):
    """az in degrees, + = right. Source is behind the listener: duller overall, far ear delayed, shadowed."""
    s = np.sin(np.radians(az))
    sig = bp(sig, 30, 5200) * gain
    near, far = (1, 0) if s >= 0 else (0, 1)
    itd = 0.00066 * abs(s)
    put(room, sig, t, near)
    put(room, bp(sig, 30, 1500 + 3500 * (1 - abs(s))) * (1 - 0.62 * abs(s)), t + itd, far)

# ---- the test itself --------------------------------------------------------------------------
for tn in TL["tones"]:
    t = seg(tn["t0"], tn["t1"]); x = np.sin(2 * np.pi * tn["f"] * t) * tn["g"]
    na = int(0.06 * SR); x[:na] *= np.linspace(0, 1, na)
    if not tn.get("hardEnd"): x[-na:] *= np.linspace(1, 0, na)
    for ch in ((0,) if tn["ch"] == "L" else (1,) if tn["ch"] == "R" else (0, 1)): put(dry, x, tn["t0"], ch)
for tx in TL["texts"]:                       # soft UI tick on every new instruction
    t = seg(0, 0.05); x = np.sin(2 * np.pi * 1400 * t) * np.exp(-t / 0.012) * 0.04
    put(dry, x, tx["t"], 0); put(dry, x, tx["t"], 1)

# ---- what is not the test ---------------------------------------------------------------------
def step():
    t = seg(0, 0.7); x = np.zeros(len(t))
    heel = np.sin(2 * np.pi * 68 * t) * np.exp(-t / 0.05) + bp(noise(len(t)), 90, 900) * np.exp(-t / 0.025) * 0.8
    toe = np.roll(np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.035) * 0.5 + bp(noise(len(t)), 200, 1600) * np.exp(-t / 0.02) * 0.4, int(0.13 * SR)); toe[:int(0.13 * SR)] = 0
    c = seg(0, 0.22); f = np.linspace(rng.uniform(260, 330), rng.uniform(360, 460), len(c))
    creak = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.sin(np.pi * c / c[-1]) ** 2 * 0.12
    x += heel + toe; x[int(0.2 * SR):int(0.2 * SR) + len(creak)] += bp(creak, 200, 2400)
    return x
def breath(dur, g0, g1):
    t = seg(0, dur); k = t / t[-1]; ph = (t % 2.6) / 2.6
    inh = np.where(ph < 0.38, np.sin(np.pi * ph / 0.38) ** 2, 0)
    exh = np.where((ph > 0.46) & (ph < 0.95), np.clip(np.sin(np.pi * (ph - 0.46) / 0.49), 0, 1) ** 1.5, 0)
    x = bp(noise(len(t)), 700, 2800) * inh * 0.7 + bp(noise(len(t)), 300, 1500) * exh
    return x * (g0 + (g1 - g0) * k ** 1.5)
def knock():
    x = np.zeros(int(1.0 * SR))
    for j in range(3):
        t = seg(0, 0.25); k = (np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.035) + 0.5 * np.sin(2 * np.pi * 430 * t) * np.exp(-t / 0.018) + bp(noise(len(t)), 900, 4000) * np.exp(-t / 0.004) * 0.6)
        i = int(j * 0.21 * SR); x[i:i + len(k)] += k * (1, 0.85, 1.1)[j]
    return x
def exhale():
    t = seg(0, 0.9); return bp(noise(len(t)), 350, 4500) * np.minimum(1, t / 0.04) * np.exp(-t / 0.28)

for s in TL["sounds"]:
    if s["k"] == "step": place(step(), s["t"], s["az"], s["g"])
    elif s["k"] == "breath":
        x = breath(s["dur"], s["g0"], s["g1"]); n = int(0.4 * SR); x[:n] *= np.linspace(0, 1, n); x[-200:] *= np.linspace(1, 0, 200)
        place(x, s["t"], s["az"], 1.0)
    elif s["k"] == "knock": place(knock(), s["t"], s["az"], s["g"])
    elif s["k"] == "exhale": place(exhale(), s["t"], s["az"], s["g"])

# room reverb only on the things that are in the room with you
ir_n = int(0.9 * SR); L = N + ir_n
for c in range(2):
    ir = noise(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.22); ir /= np.sqrt((ir ** 2).sum())
    room[:, c] += np.fft.irfft(np.fft.rfft(room[:, c], L) * np.fft.rfft(ir, L), L)[:N] * 0.3

# hook: one soft click so people check their earphones
t = seg(0, 0.05); x = np.sin(2 * np.pi * 1400 * t) * np.exp(-t / 0.012) * 0.06; put(dry, x, 0.1, 0); put(dry, x, 0.1, 1)

mix = dry + room
a, b = int(TL["cut"] * SR), int(TL["lastSound"] * SR); mix[a:b] = 0     # black, dead air, then one breath in your right ear
mix = mix / np.abs(mix).max() * 0.82
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
