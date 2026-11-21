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

OFF, SH0, SH1, COR = TL["dead"], TL["shift"][0], TL["shift"][1], TL["corrupt"]

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
ft, iv = TL["flood"] + 0.5, 0.27          # one tick per spawned line (mirrors scene_tv.html)
while ft < OFF:
    x = seg(0, 0.05); add(bp(noise(len(x)), 300, 2400) * np.exp(-x / 0.012), ft, 0.5, pan=rng.uniform(-.5, .5))
    ft += iv; iv = max(0.016, iv * 0.88)

# power off: thunk + collapsing whine, then nothing at all
BANG, CUT, LE = TL["bang"], TL["cut"], TL["linesEnd"]
add(thud(60, 0.7, 0.1, 1.0), OFF, 0.9)
x = seg(0, 1.2); add((np.sin(2 * np.pi * 73 * x) + 0.6 * np.sin(2 * np.pi * 110 * x)) * np.exp(-x / 0.3), TL["flood"], 0.9)   # the first one lands
x = seg(0, 0.4); add(fade(np.sin(2 * np.pi * np.cumsum(np.linspace(9000, 1500, len(x))) / SR), 0.002, 0.2), OFF, 0.08)

# the dark stare: almost silent. room tone, then breathing close to one ear that is not yours
t = seg(OFF + 1.0, BANG - 0.35); add(fade(bp(noise(len(t)), 50, 260), 1.0, 0.02), OFF + 1.0, 0.12)
t = seg(LE, BANG - 0.35); k = t / t[-1]
br = np.clip(np.sin(2 * np.pi * 0.36 * t - 1.2), 0, 1) ** 1.4 + 0.55 * np.clip(np.sin(2 * np.pi * 0.36 * t - 1.2 + np.pi), 0, 1) ** 2
add(fade(bp(noise(len(t)), 300, 1500) * br * (0.04 + 0.96 * k ** 2.2), 0.3, 0.004), LE, 2.6, pan=0.75)
for j in range(4):                      # one floorboard, behind and to the right
    x = seg(0, 0.09); f0 = rng.uniform(210, 360)
    add(bp(np.sign(np.sin(2 * np.pi * f0 * x * (1 + 2 * x))) * np.exp(-x / 0.035), 180, 2200), LE + 1.7 + j * 0.13, 0.7, pan=0.6)

# found: everything at once after 0.35 s of dead air
t = seg(BANG, CUT)
saw = lambda f: 2 * ((f * t) % 1) - 1
st_ = bp(sum(saw(f) for f in (110, 116.5, 155.6, 311.1, 329.6, 466.2, 493.9, 932.3, 987.8)) * 0.1, 60, 6000)
shr = bp(noise(len(t)), 1500, 9000) * (0.6 + 0.4 * np.sin(2 * np.pi * 37 * t))
add(fade(st_ * 1.3 + shr * 0.9 + bp(noise(len(t)), 300, 9000) * 0.5, 0.001, 0.002), BANG, 1.6)
add(thud(42, 0.6, 0.3, 1.0), BANG, 2.0)

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
