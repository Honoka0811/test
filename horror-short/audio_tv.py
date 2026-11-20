"""Soundtrack for the emergency-broadcast short (all synthesized) -> audio.wav"""
import json, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.environ.get("TIMELINE") or os.path.join(HERE, "tv.json")))
SR = 44100
N = int(TL["end"] * SR)
rng = np.random.default_rng(7)
mix = np.zeros((N, 2))

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
def seg(t0, t1): return np.arange(int((t1 - t0) * SR)) / SR
def fade(x, a=0.01, r=0.01):
    na, nr = max(1, int(a * SR)), max(1, int(r * SR)); x = x.copy()
    x[:na] *= np.linspace(0, 1, na); x[-nr:] *= np.linspace(1, 0, nr); return x
def noise(n): return rng.standard_normal(n)
def thud(f=52, dur=1.6, d=0.25, nz=0.6):
    t = seg(0, dur)
    return np.sin(2 * np.pi * f * t) * np.exp(-t / d) + bp(noise(len(t)), 40, 900) * np.exp(-t / 0.07) * nz
def sq(phase):  # soft square: first odd harmonics
    return sum(np.sin(2 * np.pi * phase * k) / k for k in (1, 3, 5, 7))

OFF, SH0, SH1, COR = TL["off"], TL["shift"][0], TL["shift"][1], TL["corrupt"]

# tape hiss + mains hum while the set is on
t = seg(0, OFF)
add(fade(bp(noise(len(t)), 1800, 9000), 0.05, 0.005), 0, 0.02)
add(fade(np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 100 * t), 0.05, 0.005), 0, 0.03)

# sign-off chime
t = seg(0, TL["signoffEnd"]); wow = 1 + 0.004 * np.sin(2 * np.pi * 0.8 * t)
ch = sum(np.sin(2 * np.pi * f * t * wow) for f in (392, 493.9, 587.3)) * np.minimum(1, t / 0.3)
add(fade(ch, 0.01, 0.01), 0, 0.16)

# static bursts
for a, b, g in [(TL["signoffEnd"], TL["alertStart"], 0.4), (SH0, SH1, 0.38), (COR, COR + 0.2, 0.4)]:
    t = seg(a, b); add(fade(bp(noise(len(t)), 400, 9000), 0.003, 0.003), a, g)

# siren: original two-chord alternation on a worn tape, dies in a tape-stop at the shift
t = seg(TL["alertStart"], SH0); n = len(t)
rate = np.ones(n) * (1 + 0.008 * np.sin(2 * np.pi * 0.7 * t))
stop = t > t[-1] - 0.6; rate[stop] *= np.linspace(1, 0.3, stop.sum())
hi = (np.floor(t / 0.62) % 2) == 0
si = np.zeros(n)
for fa, fb in [(466.2, 370.0), (493.9, 392.0)]:
    f = np.where(hi, fa, fb) * rate
    si += sq(np.cumsum(f) / SR)
si = bp(si, 200, 2800) * (0.8 + 0.2 * np.sin(2 * np.pi * 9 * t))
add(fade(si, 0.01, 0.02), TL["alertStart"], 0.26)

# per-line cues: beep while "official", low toll once the broadcast turns
for c in TL["cards"]:
    seen = set()
    for l in c["lines"]:
        tt = c["t"] + l["dt"]
        if tt in seen: continue
        seen.add(tt)
        if c.get("dark"):
            x = seg(0, 1.4); add((np.sin(2 * np.pi * 98 * x) + 0.5 * np.sin(2 * np.pi * 147.5 * x)) * np.exp(-x / 0.45), tt, 0.55)
        else:
            x = seg(0, 0.07); add(fade(np.sin(2 * np.pi * 1000 * x), 0.003, 0.01), tt, 0.3)

# dark phase drone with a slowly rising high cluster
t = seg(SH1, COR); k = t / t[-1]
dr = (np.sin(2 * np.pi * 46 * t) + np.sin(2 * np.pi * 48.4 * t)) * (0.4 + 0.6 * k)
cl = sum(np.sin(2 * np.pi * f * t * (1 + 0.06 * k) + i) for i, f in enumerate((831, 880, 1245, 1319))) * 0.04 * k ** 2
add(fade(dr * 0.32 + cl, 0.6, 0.01), SH1, 1.0)

# hijack: the siren comes back wrong, pitched down, clipping, climbing
t = seg(COR + 0.2, OFF); n = len(t); k = t / t[-1]
rate = 0.45 + 0.95 * k ** 1.5
hi = (np.floor(np.cumsum(1 / np.maximum(0.12, 0.62 * (1 - 0.8 * k))) / SR) % 2) == 0
s2 = np.zeros(n)
for fa, fb in [(466.2, 370.0), (493.9, 392.0), (233, 185)]:
    s2 += sq(np.cumsum(np.where(hi, fa, fb) * rate) / SR)
s2 = np.tanh(s2 * (1 + 5 * k)) * (0.12 + 0.6 * k ** 1.5) + bp(noise(n), 300, 8000) * 0.5 * k ** 3
add(fade(s2, 0.01, 0.002), COR + 0.2, 0.5)
ft, iv = COR + 0.7, 0.27          # one tick per spawned line (mirrors scene_tv.html)
while ft < OFF:
    x = seg(0, 0.05); add(bp(noise(len(x)), 300, 2400) * np.exp(-x / 0.012), ft, 0.5, pan=rng.uniform(-.5, .5))
    ft += iv; iv = max(0.016, iv * 0.88)

# power off: thunk + collapsing whine
add(thud(60, 0.7, 0.1, 1.0), OFF, 0.9)
x = seg(0, 0.4); add(fade(np.sin(2 * np.pi * np.cumsum(np.linspace(9000, 1500, len(x))) / SR), 0.002, 0.2), OFF, 0.08)

# dark glass: room tone, breathing that isn't yours, getting closer with every blink
G, ST, SNAP = TL["glass"], TL["stages"], TL["snap"]
t = seg(G, SNAP); k = t / t[-1]
add(fade(bp(noise(len(t)), 60, 300), 0.3, 0.01), G, 0.035)
br = np.clip(np.sin(2 * np.pi * 0.42 * t - 0.5), 0, 1) ** 1.5 + 0.6 * np.clip(np.sin(2 * np.pi * 0.42 * t - 0.5 + np.pi), 0, 1) ** 2
add(fade(bp(noise(len(t)), 350, 1700) * br * (0.08 + 0.92 * k ** 2), 0.2, 0.01), G, 0.75, pan=0.3)
for i, st in enumerate(ST):                     # each blink: a dull step, then floorboards
    add(thud(46, 0.9, 0.16, 0.5), st, 0.45 + 0.3 * i)
    for j in range(4):
        x = seg(0, 0.08); f0 = rng.uniform(220, 400)
        add(bp(np.sign(np.sin(2 * np.pi * f0 * x * (1 + 2 * x))) * np.exp(-x / 0.03), 200, 2400), st + 0.12 + j * 0.1, 0.25 + 0.15 * i, pan=0.4 - 0.2 * i)
# while the fingers close: a dry clicking rattle in the throat right behind the ear, plus rising sub
t0 = ST[2] + 0.25; tt = t0
while tt < SNAP - 0.05:
    kk = (tt - t0) / (SNAP - t0)
    burst = int(rng.integers(5, 14)); iv = rng.uniform(0.028, 0.05)
    for j in range(burst):
        x = seg(0, 0.03); f0 = rng.uniform(500, 900)
        c = (bp(noise(len(x)), 500, 3200) + np.sin(2 * np.pi * f0 * x)) * np.exp(-x / 0.006)
        if tt + j * iv < SNAP: add(c, tt + j * iv, (0.25 + 0.5 * kk) * rng.uniform(0.6, 1), pan=-0.5)
        iv *= 1.06
    tt += burst * iv + rng.uniform(0.1, 0.3) * (1 - 0.6 * kk)
t = seg(ST[2], SNAP); k = t / t[-1]
add(fade(np.sin(2 * np.pi * 38 * t) * k ** 2 + sum(np.sin(2 * np.pi * f * t) for f in (1661, 1760, 2489)) * 0.03 * k ** 3, 0.1, 0.003), ST[2], 0.8)

# the set snaps back on: sting
t = seg(SNAP, TL["cut"])
saw = lambda f: 2 * ((f * t) % 1) - 1
st_ = bp(sum(saw(f) for f in (110, 116.5, 155.6, 311.1, 329.6, 466.2, 493.9)) * 0.1, 60, 5000)
sc = bp(noise(len(t)), 900, 5000) * np.exp(-t / 0.35) * 0.6
add(fade(st_ + sc, 0.002, 0.004), SNAP, 1.3)
add(thud(40, 0.7, 0.4, 0.8), SNAP, 1.5)

# light room reverb, limiter, hard cut
ir_n = int(1.0 * SR); ir = noise(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.25); ir /= np.sqrt((ir ** 2).sum())
L = N + ir_n
for c in range(2):
    mix[:, c] += np.fft.irfft(np.fft.rfft(mix[:, c], L) * np.fft.rfft(np.roll(ir, c * 37), L), L)[:N] * 0.18
mix[int(TL["cut"] * SR):] = 0
mix /= np.abs(mix).max() / 1.6
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
