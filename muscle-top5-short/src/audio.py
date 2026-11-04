"""Original BGM + SFX synthesized from scratch, mixed with the narration.

124 BPM, A minor (Am-F-C-G). Arrangement follows build/timeline.json:
  hook   : punchy groove + riser into the countdown
  r5..r2 : full groove, layers added as ranks climb
  build  : drums cut, filtered pad, accelerating snare roll + riser
  r1     : big drop (lead + crash)
  outro  : groove, then a tail fade
"""
import json, os, wave
import numpy as np
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
SR = 44100
TL = json.load(open(os.path.join(B, "timeline.json")))
BEAT = 60 / TL["bpm"]
DUR = TL["duration"]
N = int(DUR * SR) + SR
rng = np.random.default_rng(7)
SC = {s["id"]: s for s in TL["scenes"]}


def T(n):
    return np.arange(n) / SR


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def add(buf, x, t0, gain=1.0):
    i = int(t0 * SR)
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[: j - i] * gain


def lp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return signal.sosfilt(signal.butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(f, n, detune=0.0, phase=0.0):
    t = T(n)
    return 2 * ((t * f * (1 + detune) + phase) % 1) - 1


def adsr(n, a=0.005, d=0.1, s=0.6, r=0.05):
    e = np.full(n, s)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[na:na + nd] = np.linspace(1, s, len(e[na:na + nd]))
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


# ---------------- instruments ----------------
def kick(big=False):
    n = int(0.45 * SR); t = T(n)
    f = 45 + 120 * np.exp(-t * 28)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (5 if big else 7.5))
    x[:200] += rng.normal(0, 0.5, 200) * np.linspace(1, 0, 200)
    return np.tanh(x * 1.6)


def clap():
    n = int(0.25 * SR); t = T(n)
    nz = bp(rng.normal(0, 1, n), 900, 5000)
    env = np.exp(-t * 18)
    for k in (0.0, 0.011, 0.022):  # flam
        env += np.where(t >= k, np.exp(-(t - k) * 120), 0) * 0.6
    return nz * env * 0.6


def snare():
    n = int(0.18 * SR); t = T(n)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    nz = hp(rng.normal(0, 1, n), 1500) * np.exp(-t * 22)
    return (body * 0.5 + nz * 0.6)


def hat(open_=False):
    n = int((0.22 if open_ else 0.05) * SR); t = T(n)
    return hp(rng.normal(0, 1, n), 7000) * np.exp(-t * (14 if open_ else 80)) * 0.35


def crash():
    n = int(2.2 * SR); t = T(n)
    return hp(rng.normal(0, 1, n), 4000) * np.exp(-t * 2.2) * 0.45


def supersaw(m, n, voices=5, spread=0.012):
    x = np.zeros(n)
    for v in range(voices):
        d = (v - (voices - 1) / 2) * spread / (voices - 1) * 2
        x += saw(midi(m), n, d, rng.random())
    return x / voices


def pluck(m, dur=0.22):
    n = int(dur * SR); t = T(n)
    x = supersaw(m, n, 3, 0.008) + 0.5 * np.sin(2 * np.pi * midi(m + 12) * t)
    x = lp(x, 5200) * np.exp(-t * 11)
    return x


def bass(m, dur):
    n = int(dur * SR)
    x = saw(midi(m), n) * 0.7 + np.sin(2 * np.pi * midi(m) * T(n)) * 0.6
    return np.tanh(lp(x, 900) * 1.5) * adsr(n, 0.004, 0.08, 0.7, 0.03)


def impact():
    n = int(1.6 * SR); t = T(n)
    f = 30 + 90 * np.exp(-t * 6)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.5)
    crack = lp(rng.normal(0, 1, n), 3500) * np.exp(-t * 9)
    return np.tanh((boom * 1.4 + crack * 0.5) * 1.3)


def whoosh(dur=0.45, up=True):
    n = int(dur * SR); t = T(n)
    nz = rng.normal(0, 1, n)
    out = np.zeros(n); blk = 256
    for i in range(0, n, blk):
        p = i / n if up else 1 - i / n
        fc = 300 + 6000 * p ** 2
        out[i:i + blk] = bp(nz[i:i + blk], fc * 0.7, min(fc * 1.4, 19000))
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return out * env * 0.9


def riser(dur):
    n = int(dur * SR); t = T(n)
    p = t / dur
    nz = rng.normal(0, 1, n); out = np.zeros(n); blk = 512
    for i in range(0, n, blk):
        fc = 400 + 9000 * (i / n) ** 2
        out[i:i + blk] = bp(nz[i:i + blk], fc * 0.6, min(fc * 1.5, 19000))
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * p ** 2) / SR) * 0.25
    return (out * 0.5 + tone) * p ** 2


def pop(m=84):
    n = int(0.25 * SR); t = T(n)
    f = midi(m) * (1 + 0.6 * np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * 0.6


def ding(m=88):
    n = int(1.2 * SR); t = T(n)
    x = sum(np.sin(2 * np.pi * midi(m) * k * t) * np.exp(-t * (3 + k * 2)) / k for k in (1, 2.01, 3.03))
    return x * 0.4


def sparkle():
    out = np.zeros(int(1.4 * SR))
    for i, m in enumerate([88, 91, 95, 100, 103, 107]):
        add(out, ding(m) * 0.5, i * 0.07)
    return out


# ---------------- arrangement ----------------
CHORDS = [(57, [69, 72, 76]), (53, [69, 72, 77]), (48, [67, 72, 76]), (55, [67, 71, 74])]  # Am F C G
drums = np.zeros(N); music = np.zeros(N); fx = np.zeros(N)


def section(t):
    for s in TL["scenes"]:
        if s["start"] <= t < s["end"]:
            return s["id"]
    return "outro"


nb = int(DUR / BEAT) + 1
for b in range(nb):
    t_ = b * BEAT
    sec = section(t_)
    bar, beat_in_bar = divmod(b, 4)
    root, chord = CHORDS[bar % 4]
    in_build = sec == "build"
    rank = SC[sec].get("rank") or 0
    if not in_build:
        drums_k = kick(big=sec == "r1")
        add(drums, drums_k, t_, 0.95)
        if beat_in_bar in (1, 3):
            add(drums, clap(), t_, 0.7)
        add(drums, hat(True), t_ + BEAT / 2, 0.55)
        if sec in ("r3", "r2", "r1", "outro"):
            for k in (0.25, 0.75):
                add(drums, hat(), t_ + BEAT * k, 0.5)
        # offbeat pumping bass
        add(music, bass(root - 12, BEAT * 0.45), t_ + BEAT / 2, 0.55)
        # pad: supersaw chord per beat, sidechained by shape
        n = int(BEAT * SR); tt = T(n)
        pump = np.clip(tt / (BEAT * 0.55), 0, 1) ** 1.6
        pad = sum(supersaw(m, n) for m in chord) / 3
        pad = lp(pad, 2600 if sec != "r1" else 4200) * pump
        add(music, pad, t_, 0.32 if sec != "hook" else 0.22)
        # arp from r4 onward, lead melody on r1
        if sec in ("r4", "r3", "r2", "r1", "outro") or sec == "hook":
            arp = chord + [chord[0] + 12]
            for k in range(4 if sec != "hook" else 2):
                m = arp[(b * 4 + k) % 4] + (12 if sec in ("r2", "r1") and k % 2 else 0)
                add(music, pluck(m), t_ + k * BEAT / (4 if sec != "hook" else 2), 0.28)
        if sec == "r1":
            mel = [76, 79, 81, 79, 76, 74, 72, 74]
            m = mel[b % 8]
            n = int(BEAT * 0.9 * SR)
            lead = lp(supersaw(m + 12, n, 7, 0.02), 6000) * adsr(n, 0.01, 0.2, 0.6, 0.08)
            add(music, lead, t_, 0.22)
    else:
        # build: filtered held pad, no kick
        n = int(BEAT * SR)
        pad = sum(supersaw(m, n) for m in chord) / 3
        add(music, lp(pad, 700), t_, 0.3)

# --- build section: snare roll accelerating + riser, silence right before drop
bs = SC["build"]["start"]; be = SC["build"]["end"]
t_ = bs + BEAT * 2
while t_ < be - 0.12:
    p = (t_ - bs) / (be - bs)
    add(drums, snare(), t_, 0.25 + 0.6 * p)
    t_ += BEAT / (2 if p < 0.35 else 4 if p < 0.7 else 8)
add(fx, riser(be - bs - 0.1), bs, 0.7)

# --- risers / impacts / sfx tied to the visuals
add(fx, impact(), 0.0, 0.9)
add(fx, riser(BEAT * 4), SC["r5"]["start"] - BEAT * 4, 0.45)
for s in TL["scenes"]:
    if s.get("rank"):
        add(fx, whoosh(0.35), s["start"] - 0.3, 0.6)
        add(fx, impact(), s["start"], 1.0 if s["rank"] == 1 else 0.75)
        add(drums, crash(), s["start"], 0.6 if s["rank"] == 1 else 0.35)
        for li, ln in enumerate(s["lines"][1:3], 1):
            add(fx, pop(84 + li * 3), ln["start"], 0.5)
        add(fx, whoosh(0.3, up=False), s["lines"][3]["start"] - 0.1, 0.35)
    if s["rank"] == 1:
        add(fx, sparkle(), s["start"] + 0.1, 0.55)
hk = SC["hook"]["lines"][1]["start"]
add(fx, whoosh(0.3), hk - 0.15, 0.5)
ol = SC["outro"]["lines"]
add(fx, pop(86), ol[0]["start"], 0.45)
add(fx, ding(91), ol[1]["start"] + 0.1, 0.6)

# ---------------- narration + ducking ----------------
voice = np.zeros(N); active = np.zeros(N)
for s in TL["scenes"]:
    for ln in s["lines"]:
        with wave.open(ln["wav"]) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
            assert w.getframerate() == SR
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
        add(voice, x, ln["start"])
        i, j = int(ln["start"] * SR), int((ln["start"] + ln["dur"]) * SR)
        active[i:j] = 1
# smooth duck envelope (fast attack, slower release)
k = int(0.12 * SR)
duck = np.convolve(active, np.ones(k) / k, mode="same")
duck = np.maximum(duck, np.roll(duck, -int(0.05 * SR)))
bgm_gain = 1.0 - 0.55 * np.clip(duck, 0, 1)

bgm = (drums * 0.9 + music) * 0.55
# end fade
fade = np.ones(N); fs = int((DUR - 1.4) * SR)
fade[fs:] = np.linspace(1, 0, N - fs) ** 2
mix = bgm * bgm_gain * fade + fx * 0.5 * fade + voice * 1.0
mix = hp(mix, 30)
# gentle limiter
peak = np.max(np.abs(mix))
mix = np.tanh(mix / peak * 1.6) / np.tanh(1.6) * 0.95
mix = mix[: int(DUR * SR)]

out = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
with wave.open(os.path.join(B, "mix.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
bg = (np.tanh(bgm * fade / (np.max(np.abs(bgm)) + 1e-9) * 1.3) * 0.9 * 32767).astype(np.int16)[: int(DUR * SR)]
with wave.open(os.path.join(B, "bgm_only.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bg.tobytes())
print("mix.wav written", round(DUR, 2), "s")
