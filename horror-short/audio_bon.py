"""Soundtrack for the bon-dance short (all synthesized) -> audio.wav
Only drum, plucked string and hand claps - no sine tones, no synthetic flute or bells.
The band plays on the exact eighth-note grid the dancers follow (bon.json), slows to a halt, then stops dead."""
import json, wave, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.environ.get("TIMELINE") or os.path.join(HERE, "bon.json")))
SR = 44100
N = int(TL["end"] * SR)
rng = np.random.default_rng(17)
mix = np.zeros((N, 2)); band = np.zeros((N, 2))

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

def don(g=1.0):                 # big drum: skin thump + stick noise
    t = seg(0, 0.9); return (np.sin(2 * np.pi * (62 * t + 40 * (1 - np.exp(-t * 28)) / 28)) * np.exp(-t / 0.2) + bp(noise(len(t)), 80, 1400) * np.exp(-t / 0.03) * 0.9) * g
def ka():                       # stick on the wooden rim
    t = seg(0, 0.12); return bp(noise(len(t)), 900, 5000) * np.exp(-t / 0.01)
def claps():                    # a ring of people clapping not quite together
    x = np.zeros(int(0.3 * SR))
    for j in range(9):
        t = seg(0, 0.12); c = bp(noise(len(t)), 900 + rng.uniform(-200, 300), 3800) * np.exp(-t / rng.uniform(0.008, 0.016))
        i = int(abs(rng.normal(0, 0.012)) * SR); x[i:i + len(c)] += c * rng.uniform(0.5, 1)
    return x
def shami(f, dur=0.7):          # plucked string with the slap of the plectrum
    n = max(2, int(round(SR / f))); buf = rng.uniform(-1, 1, n); out = np.empty(int(dur * SR))
    for i in range(len(out)):
        j = i % n; out[i] = buf[j]; buf[j] = 0.993 * 0.5 * (buf[j] + buf[(j + 1) % n])
    t = seg(0, dur); out = bp(out, 150, 6000) + bp(noise(len(t)), 1500, 6000) * np.exp(-t / 0.004) * 0.6
    return out * np.exp(-t / 0.35)

A3, C4, D4, E4, G4, A4 = 220.0, 261.6, 293.7, 329.6, 392.0, 440.0
mel = [E4, 0, G4, E4, D4, C4, D4, 0, E4, D4, C4, A3, C4, 0, A3, 0, E4, 0, G4, A4, G4, E4, D4, 0, C4, D4, E4, D4, C4, A3, A3, 0]
for E in (TL["eighths1"], TL["eighths2"]):
    for i, tt in enumerate(E):
        b = i % 8
        if b in (0, 2, 4): put(band, don(), tt, 0.9)
        if b == 7: put(band, don(0.6), tt, 0.6)
        if b in (3, 5, 6): put(band, ka(), tt, 0.45, pan=0.2)
        if i % 16 in (12, 14): put(band, claps(), tt, 0.4)                 # the dancers clap on beats 7 and 8
        f = mel[i % len(mel)]
        if f: put(band, shami(f), tt, 0.5, pan=-0.2)
band = reverb2(band, 0.28, 0.22)
for E in (TL["eighths1"], TL["eighths2"]):                                # fade in at the start of each festival, cut dead at the end
    a = int(E[0] * SR); n = int(0.5 * SR); band[a:a + n] *= np.linspace(0, 1, n)[:, None]
stop1, start2, stop2 = TL["scenes"][3]["t"], TL["eighths2"][0], 39.0
band[int(stop1 * SR):int(start2 * SR)] = 0; band[int(stop2 * SR):] = 0
mix += band

# hook: two drum strokes in the dark
put(mix, don(), 0.1, 1.0); put(mix, don(), 1.25, 1.0)

# after it stops: only night air and a low pressure
t = seg(stop1 + 0.3, start2); put(mix, fade(bp(noise(len(t)), 90, 600) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t)), 0.6, 0.3), stop1 + 0.3, 0.05)
t = seg(stop1, 28.6); k = t / t[-1]
put(mix, fade((np.sin(2 * np.pi * 41 * t) + np.sin(2 * np.pi * 43.4 * t)) * k * 0.5, 0.5, 0.01), stop1, 0.8)
SC = [(s["k"], s["t"]) for s in TL["scenes"]]
put(mix, don(), 23.6, 0.9); put(mix, don(), 26.6, 1.3)
put(mix, don(0.8), 28.9, 0.8)                                              # "he died that winter"
t = seg(39.0, TL["finalText"] - 1.0); put(mix, fade(bp(noise(len(t)), 90, 600), 0.6, 0.3), 39.0, 0.04)

# "you counted just now": one stroke. then they are all looking at you.
put(mix, don(), TL["finalText"], 1.2)
put(mix, don(), 47.0, 1.4); x = seg(0, 2.5); put(mix, np.sin(2 * np.pi * 36 * x) * np.exp(-x / 0.8), 47.0, 0.9)
put(mix, don(), 48.2, 1.0)

mix[int(TL["cut"] * SR):] = 0
mix /= np.abs(mix).max() / 1.4
mix = np.tanh(mix) * 0.97
w = wave.open(os.path.join(HERE, "audio.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("audio ok", N / SR, "s")
