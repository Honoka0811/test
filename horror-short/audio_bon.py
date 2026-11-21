"""Soundtrack for the bon-dance short (all synthesized) -> audio.wav
A festival band (taiko, hand gong, bamboo flute) that slows and sags like a dying tape, then stops dead."""
import json, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.environ.get("TIMELINE") or os.path.join(HERE, "bon.json")))
SR = 44100
N = int(TL["end"] * SR)
rng = np.random.default_rng(17)
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
def put(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i < 0: return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig), 0] += sig * gain * (1 - max(0, pan)); buf[i:i + len(sig), 1] += sig * gain * (1 + min(0, pan))
def reverb2(buf, tau, wet):
    n = int(tau * 5 * SR); L = len(buf) + n; out = buf.copy()
    for c in range(2):
        ir = noise(n) * np.exp(-np.arange(n) / SR / tau); ir /= np.sqrt((ir ** 2).sum())
        out[:, c] += np.fft.irfft(np.fft.rfft(buf[:, c], L) * np.fft.rfft(ir, L), L)[:len(buf)] * wet
    return out

def don(g=1.0):                 # big drum, centre of the skin
    t = seg(0, 0.9); return (np.sin(2 * np.pi * (62 * t + 40 * (1 - np.exp(-t * 28)) / 28)) * np.exp(-t / 0.2) + bp(noise(len(t)), 80, 1200) * np.exp(-t / 0.025) * 0.7) * g
def ka():                       # stick on the rim
    t = seg(0, 0.12); return (bp(noise(len(t)), 1200, 6000) * np.exp(-t / 0.008) + np.sin(2 * np.pi * 950 * t) * np.exp(-t / 0.02) * 0.5)
def kane():                     # small hand gong
    t = seg(0, 0.35); return sum(a * np.sin(2 * np.pi * f * t) for f, a in [(2610, 1), (3920, 0.6), (5310, 0.35)]) * np.exp(-t / 0.07)
def flute(f, dur):
    t = seg(0, dur); vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.15)
    ph = np.cumsum(f * vib) / SR
    x = np.sin(2 * np.pi * ph) + 0.28 * np.sin(4 * np.pi * ph) + 0.1 * np.sin(6 * np.pi * ph) + bp(noise(len(t)), 2500, 9000) * 0.05
    return fade(x, 0.035, 0.05)

# ---- the band, written at steady tempo, then bent ------------------------------------------------
BEAT = 60 / 104; E8 = BEAT / 2
M0, M1 = TL["musicStart"], TL["musicStop"]
ML = int((M1 - M0 + 4) * SR); band = np.zeros((ML, 2))
A4, C5, D5, E5, G5, A5 = 440.0, 523.3, 587.3, 659.3, 784.0, 880.0
mel = [E5, 0, G5, E5, D5, C5, D5, 0, E5, D5, C5, A4, C5, 0, A4, 0, E5, 0, G5, A5, G5, E5, D5, 0, C5, D5, E5, D5, C5, A4, A4, 0]
i = 0; tt = 0.0
while tt < ML / SR - 1:
    b = i % 8
    if b in (0, 2, 4): put(band, don(), tt, 0.9)
    if b == 7: put(band, don(0.6), tt, 0.6)
    if b in (3, 5, 6): put(band, ka(), tt, 0.35, pan=0.2)
    if b % 2 == 1: put(band, kane(), tt, 0.1, pan=-0.4)
    f = mel[i % len(mel)]
    if f: n = 1 + (mel[(i + 1) % len(mel)] == 0); put(band, flute(f, E8 * n * 0.96), tt, 0.2, pan=-0.15)
    i += 1; tt += E8
band = reverb2(band, 0.3, 0.25)
# warp: from warpStart the whole band sags in pitch and tempo together
W0 = TL["warpStart"] - M0; n_out = int((M1 - M0) * SR); to = np.arange(n_out) / SR
speed = np.where(to < W0, 1.0, 1.0 - 0.3 * np.clip((to - W0) / (M1 - M0 - W0), 0, 1) ** 1.4)
src = np.cumsum(speed) / SR * SR
for c in range(2):
    y = np.interp(src, np.arange(ML), band[:, c]); y[:int(0.4 * SR)] *= np.linspace(0, 1, int(0.4 * SR))
    put(mix, np.stack([y, y], 1)[:, 0] if False else y, M0, 1.0, pan=(1 if c == 0 else -1))

# hook: two drum strokes in the dark
put(mix, don(), 0.1, 1.0); put(mix, don(), 1.25, 1.0)

# after it stops: crickets and a little wind, nothing else
t = seg(M1 + 0.4, TL["finalText"])
ch = np.sin(2 * np.pi * 4600 * t) * (np.sin(2 * np.pi * 31 * t) > 0.2) * ((t % 0.62) < 0.11)
put(mix, fade(ch, 0.5, 0.3), M1 + 0.4, 0.035, pan=0.5)
ch2 = np.sin(2 * np.pi * 5200 * t) * (np.sin(2 * np.pi * 37 * t) > 0.2) * (((t + 0.3) % 0.81) < 0.09)
put(mix, fade(ch2, 0.5, 0.3), M1 + 0.4, 0.025, pan=-0.6)
put(mix, fade(bp(noise(len(t)), 100, 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t)), 0.6, 0.3), M1 + 0.4, 0.04)
t = seg(M1, 32.6); k = t / t[-1]                      # dread under the stillness
put(mix, fade((np.sin(2 * np.pi * 41 * t) + np.sin(2 * np.pi * 43.4 * t)) * k * 0.5 + sum(np.sin(2 * np.pi * f * t + j) for j, f in enumerate((831, 880, 1245))) * 0.03 * k ** 2, 0.5, 0.01), M1, 0.9)
SC = {s["k"]: s["t"] for s in TL["scenes"]}
put(mix, don(), SC["facing"], 0.9); put(mix, don(), SC["closer"], 1.3)
x = seg(0, 2.0); put(mix, np.sin(2 * np.pi * 36 * x) * np.exp(-x / 0.6), SC["closer"], 1.0)

# "you counted just now": one stroke. then they are in front of you.
put(mix, don(), TL["finalText"], 1.2)
F0, CUT = TL["flash"], TL["cut"]
tt = F0; iv = 0.13
while tt < CUT: put(mix, don(0.9), tt, 1.1); tt += iv; iv = max(0.05, iv * 0.9)
t = seg(F0, CUT)
shr = sum(np.sin(2 * np.pi * f * t * (1 + 0.02 * np.sin(2 * np.pi * 7 * t + j)) ) for j, f in enumerate((1568, 1661, 2093, 2217, 2794))) * 0.16 + bp(noise(len(t)), 2500, 9000) * 0.25
put(mix, fade(shr, 0.003, 0.003), F0, 1.0)

a, b = int((TL["finalText"] - 1.2) * SR), int(TL["finalText"] * SR); mix[a:b] = 0     # dead air before the accusation
mix[int(CUT * SR):] = 0
mix /= np.abs(mix).max() / 1.5
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
