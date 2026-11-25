# Synthesizes an original upbeat BGM loop and sound effects (no third-party audio, no copyright issues).
# Usage: python3 music.py [out_dir]   -> bgm.wav, whoosh.wav, pop.wav, drumroll.wav, reveal.wav, ding.wav
import os, sys, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "sfx")
os.makedirs(out, exist_ok=True)


def save(name, x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    x = x / max(1e-9, np.abs(x).max()) * 0.89
    with wave.open(os.path.join(out, name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def t(sec): return np.arange(int(sec * SR)) / SR
def env(n, a=0.005, d=0.2):
    tt = np.arange(n) / SR
    return np.minimum(1, tt / a) * np.exp(-tt / d)
def lowpass(x, k):  # simple one-pole lowpass, k in (0,1]
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc); y[i] = acc
    return y
def note(midi): return 440 * 2 ** ((midi - 69) / 12)


# ---------------- BGM: 4-bar loop, 124 BPM, I-V-vi-IV in D major ----------------
BPM = 124
beat = 60 / BPM
bar = beat * 4
LOOP_BARS = 8
loop = np.zeros(int(bar * LOOP_BARS * SR))

def add(buf, start, sig, gain=1.0):
    s = int(start * SR); e = min(len(buf), s + len(sig))
    if s < len(buf): buf[s:e] += sig[: e - s] * gain

def kick():
    tt = t(0.35); f = 50 + 110 * np.exp(-tt * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)
def clap():
    n = rng.standard_normal(int(0.2 * SR))
    e = env(len(n), 0.001, 0.06)
    return (n - lowpass(n, 0.25)) * e
def hat(open_=False):
    n = rng.standard_normal(int((0.18 if open_ else 0.05) * SR))
    return (n - lowpass(n, 0.6)) * env(len(n), 0.001, 0.05 if open_ else 0.012)
def pluck(freq, dur=0.32):
    tt = t(dur)
    s = sum(np.sin(2 * np.pi * freq * h * tt) / h ** 1.4 for h in range(1, 6))
    return s * env(len(tt), 0.003, 0.12)
def bass(freq, dur):
    tt = t(dur)
    s = np.sin(2 * np.pi * freq * tt) + 0.35 * np.sign(np.sin(2 * np.pi * freq * tt))
    return lowpass(s, 0.08) * np.minimum(1, tt / 0.01) * np.exp(-tt / 0.6)

# chords (root midi, chord tones) : D  A  Bm  G
PROG = [(50, [62, 66, 69]), (45, [61, 64, 69]), (47, [62, 66, 71]), (43, [62, 67, 71])]
for b in range(LOOP_BARS):
    root, tones = PROG[b % 4]
    t0 = b * bar
    for k in range(4):
        add(loop, t0 + k * beat, kick(), 0.9)
        if k in (1, 3): add(loop, t0 + k * beat, clap(), 0.35)
    for k in range(8):
        add(loop, t0 + k * beat / 2, hat(k % 2 == 1 and k == 7), 0.12 if k % 2 else 0.07)
    for k, off in enumerate([0, 0.75, 1.5, 2.0, 2.75, 3.5]):     # syncopated bass
        add(loop, t0 + off * beat, bass(note(root), 0.32), 0.45)
    pattern = [0, 1, 2, 1, 0, 2, 1, 2]                            # arpeggiated plucks (8ths)
    for k, idx in enumerate(pattern):
        add(loop, t0 + k * beat / 2, pluck(note(tones[idx] + 12)), 0.16)
    if b % 2 == 1:                                                # little melody hook every other bar
        for k, m in enumerate([tones[2] + 12, tones[1] + 12, tones[2] + 12, tones[0] + 24]):
            add(loop, t0 + (2 + k * 0.5) * beat, pluck(note(m), 0.25), 0.12)
# soft sidechain-style pump on everything except kick for groove
pump = np.ones(len(loop))
for i in range(int(LOOP_BARS * 4)):
    s = int(i * beat * SR); n = int(0.18 * SR)
    pump[s:s + n] = np.minimum(pump[s:s + n], 0.55 + 0.45 * np.arange(n) / n)
loop = loop * (0.6 + 0.4 * pump)
bgm = np.tile(loop, 6)                                            # ~93 s, trimmed later
save("bgm.wav", bgm)

# ---------------- SFX ----------------
# whoosh: band-passed noise with rising then falling sweep
n = int(0.38 * SR); noise = rng.standard_normal(n); tt = np.arange(n) / SR
sweep = np.empty(n); acc = 0.0
for i in range(n):
    k = 0.02 + 0.5 * np.sin(np.pi * i / n) ** 2
    acc += k * (noise[i] - acc); sweep[i] = acc
save("whoosh.wav", (sweep - lowpass(sweep, 0.05)) * np.sin(np.pi * tt / tt[-1]) ** 2)

# pop: punchy pitch-drop blip for rank reveals
tt = t(0.22); f = 900 * np.exp(-tt * 18) + 180
save("pop.wav", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 14) + 0.5 * kick()[: len(tt)])

# drumroll: accelerating snare hits with crescendo (1.2 s)
roll = np.zeros(int(1.2 * SR)); tpos = 0.0; gap = 0.07
while tpos < 1.15:
    hit = rng.standard_normal(int(0.06 * SR)); hit = (hit - lowpass(hit, 0.3)) * env(len(hit), 0.001, 0.02)
    add(roll, tpos, hit, 0.3 + 0.7 * tpos / 1.15); tpos += gap; gap = max(0.028, gap * 0.94)
save("drumroll.wav", roll)

# reveal: crash cymbal + bright major chord stab
tt = t(1.6); crash = rng.standard_normal(len(tt)); crash = (crash - lowpass(crash, 0.4)) * np.exp(-tt * 2.5)
stab = sum(np.sin(2 * np.pi * note(m) * tt) for m in [74, 78, 81, 86]) * np.exp(-tt * 3)
save("reveal.wav", crash * 0.6 + stab * 0.35 + np.pad(kick(), (0, len(tt) - len(kick()))))

# ding: two-note chime for the outro / CTA
tt = t(1.0)
ding = sum(np.sin(2 * np.pi * note(m) * tt) * np.exp(-tt * 4) for m in [86, 93]) + 0.3 * np.sin(2 * np.pi * note(98) * tt) * np.exp(-tt * 6)
save("ding.wav", ding)
print("written to", out)
