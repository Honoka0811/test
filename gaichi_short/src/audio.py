"""Original BGM + SFX synthesis and final mix (all sounds generated here)."""
import numpy as np, wave, os
from scipy.signal import butter, sosfilt, resample_poly
from timeline import build, VOICE, HERE

SR = 44100
rng = np.random.default_rng(7)
BPM = 128
BEAT = 60 / BPM
STEP = BEAT / 4

def t_arr(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], "band", fs=SR, output="sos"), x)
def saw(f, t): return 2 * ((f * t) % 1.0) - 1

def kick():
    t = t_arr(0.45)
    f = 45 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / 0.22)
    x[:200] += rng.standard_normal(200) * 0.3 * np.linspace(1, 0, 200)
    return np.tanh(x * 1.6) * 0.9

def clap():
    t = t_arr(0.3)
    n = bp(rng.standard_normal(len(t)), 900, 5000)
    env = np.exp(-t / 0.09)
    for d in (0.0, 0.012, 0.024):
        env += (t >= d) * np.exp(-np.maximum(t - d, 0) / 0.006) * 0.6
    return n * env * 0.5

def hat(open_=False):
    d = 0.25 if open_ else 0.05
    t = t_arr(d + 0.05)
    n = hp(rng.standard_normal(len(t)), 7000)
    return n * np.exp(-t / (0.07 if open_ else 0.012)) * (0.22 if open_ else 0.18)

def bass(f, d):
    t = t_arr(d)
    x = saw(f, t) + 0.5 * np.sin(2 * np.pi * f * t)
    x = lp(x, 380)
    env = np.minimum(1, t / 0.005) * np.exp(-t / (d * 0.9))
    return np.tanh(x * env * 1.8) * 0.42

def pluck(f, bright=1.0):
    t = t_arr(0.35)
    x = saw(f, t) * 0.6 + saw(f * 1.006, t) * 0.4
    x = lp(x, 1800 + 2600 * bright)
    return x * np.exp(-t / 0.09) * 0.16

def lead(f, d):
    t = t_arr(d)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
    x = sum(saw(f * vib * k, t) for k in (1, 1.005, 0.995)) / 3
    x = lp(x, 3200)
    env = np.minimum(1, t / 0.02) * np.minimum(1, (d - t) / 0.05)
    return x * env * 0.13

def pad(freqs, d):
    t = t_arr(d)
    x = sum(saw(f * dt, t) for f in freqs for dt in (0.997, 1.0, 1.003))
    x = lp(x / (len(freqs) * 3), 1400)
    env = np.minimum(1, t / 0.35) * np.minimum(1, (d - t) / 0.25)
    return x * env * 0.32

def impact():
    t = t_arr(2.2)
    f = 30 + 70 * np.exp(-t / 0.08)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    crash = hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.6) * 0.35
    return np.tanh((boom * 1.2 + crash)) * 0.95

def whoosh(d=0.45):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    env = np.sin(np.pi * t / d) ** 2
    lo = bp(n, 300, 1500); hi = bp(n, 1500, 6000)
    mix = lo * (1 - t / d) + hi * (t / d)
    return mix * env * 0.35

def hit():
    t = t_arr(0.5)
    f = 60 + 160 * np.exp(-t / 0.03)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)
    x += bp(rng.standard_normal(len(t)), 1000, 8000) * np.exp(-t / 0.05) * 0.4
    return np.tanh(x * 1.5) * 0.7

def tick():
    t = t_arr(0.05)
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.01) * 0.12

def riser(d):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(t)
    # filtered noise sweep in chunks
    seg = 2048
    for i in range(0, len(t), seg):
        c = min(1, i / len(t))
        f = 400 + 6000 * c ** 2
        out[i:i + seg] = bp(n[i:i + seg], f * 0.7, min(f * 1.4, 18000), 1)
    sweep = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / d) ** 2) / SR) * 0.25
    env = (t / d) ** 1.5
    # accelerating snare roll
    roll = np.zeros_like(t); tt = 0.0; gap = 0.18
    sn = clap()
    while tt < d - 0.02:
        i = int(tt * SR); L = min(len(sn), len(roll) - i)
        roll[i:i + L] += sn[:L] * (0.3 + 0.7 * tt / d)
        gap = max(0.03, gap * 0.9); tt += gap
    return (out * 0.5 + sweep) * env + roll * 0.8

def place(buf, x, at, g=1.0, pan=0.0):
    i = int(at * SR)
    if i >= buf.shape[1] or i < 0: return
    L = min(len(x), buf.shape[1] - i)
    buf[0, i:i + L] += x[:L] * g * (1 - max(0, pan))
    buf[1, i:i + L] += x[:L] * g * (1 + min(0, pan))

def read_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate(); d = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2: d = d.reshape(-1, 2).mean(1)
    if sr != SR: d = resample_poly(d, SR, sr)
    return d

def note(n):  # midi -> Hz
    return 440 * 2 ** ((n - 69) / 12)

# Am F C G
CHORDS = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [60, 64, 67]), (43, [55, 59, 62])]
LEAD_PAT = [76, None, 72, 74, 76, None, 79, None, 77, None, 76, 72, 74, None, 71, None]

def main():
    scenes, total = build()
    T = total + 0.5
    N = int(T * SR)
    music = np.zeros((2, N)); sfx = np.zeros((2, N)); voice = np.zeros((2, N))
    S = {s["key"]: s for s in scenes}

    def section(t):
        for s in scenes:
            if s["start"] <= t < s["end"]:
                k = s["key"]
                if k == "hook": return "intro"
                if k == "tease": return "off"
                if k in ("r3", "r2"): return "hype"
                if k == "r1": return "max"
                if k in ("extra", "kara", "nanyo", "hoppo"): return "calm"
                if k == "outro": return "groove"
                return "groove"
        return "off"

    K, C, HC, HO = kick(), clap(), hat(), hat(True)
    cache = {}
    def cget(key, fn):
        if key not in cache: cache[key] = fn()
        return cache[key]

    nsteps = int(T / STEP)
    for i in range(nsteps):
        t = i * STEP
        sec = section(t)
        if sec == "off": continue
        bar = i // 16; st = i % 16
        root, tones = CHORDS[bar % 4]
        if st == 0:
            g = 0.55 if sec in ("intro", "calm") else 0.75
            place(music, cget(("pad", bar % 4), lambda: pad([note(x) for x in tones], BEAT * 4)), t, g)
        if sec in ("groove", "hype", "max"):
            if st % 4 == 0: place(music, K, t, 1.0)
            if st in (4, 12): place(music, C, t, 0.9)
            if st % 2 == 0: place(music, HC, t + 0.0, 0.8, 0.3)
            if sec != "groove" and st % 4 == 2: place(music, HO, t, 0.8, -0.3)
            if sec == "max" and st % 2 == 1: place(music, HC, t, 0.5, -0.3)
            if st in (0, 3, 6, 8, 10, 11, 14):
                place(music, cget(("b", root), lambda: bass(note(root), STEP * 1.6)), t, 1.0)
        if sec in ("intro", "calm") and st % 4 == 0:
            place(music, cget(("b", root, "l"), lambda: bass(note(root), BEAT * 0.9)), t, 0.6)
        if sec in ("calm",) and st % 4 == 2: place(music, HC, t, 0.5, 0.3)
        # arp
        arp = tones + [tones[0] + 12]
        n_ = arp[[0, 1, 2, 3, 2, 1, 3, 1][st % 8]] + 12
        bright = {"intro": 0.0, "calm": 0.3, "groove": 0.6, "hype": 0.9, "max": 1.0}[sec]
        place(music, cget(("p", n_, bright), lambda: pluck(note(n_), bright)), t, 0.9, (-0.4 if st % 2 else 0.4))
        if sec in ("hype", "max"):
            ln = LEAD_PAT[st]
            if ln is not None:
                place(music, cget(("l", ln), lambda: lead(note(ln), STEP * 1.9)), t, 1.0 if sec == "max" else 0.7)

    # intro build -> title impact
    hook, title = S["hook"], S["title"]
    place(sfx, riser(1.4), title["start"] - 1.4, 0.6)
    place(sfx, impact(), title["start"], 0.9)
    # rank transitions
    for s in scenes:
        if s["key"].startswith("r") and s["key"] != "r1":
            place(sfx, whoosh(), s["start"] - 0.2, 0.8)
            place(sfx, hit(), s["start"] + 0.12, 0.8)
            for j in range(8):
                place(sfx, tick(), s["start"] + 0.5 + j * 0.07, 0.8)
        if s["key"] in ("extra", "kara", "nanyo", "hoppo", "outro"):
            place(sfx, whoosh(0.35), s["start"] - 0.15, 0.6)
    te, r1 = S["tease"], S["r1"]
    place(sfx, riser(te["end"] - te["start"]), te["start"], 0.8)
    place(sfx, impact(), r1["start"], 1.0)
    place(sfx, impact(), S["outro"]["end"] - 2.2, 0.6)

    # voice
    for s in scenes:
        v = read_wav(os.path.join(VOICE, s["key"] + ".wav"))
        place(voice, v, s["vstart"], 1.0)

    # sidechain duck music under voice
    env = np.abs(voice[0])
    env = lp(env, 6) ; env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    music *= (1 - 0.5 * env)
    # end fade
    fade = np.ones(N); fl = int(1.5 * SR); fade[-fl:] = np.linspace(1, 0, fl)
    music *= fade
    mix = music * 0.55 + sfx * 0.6 + voice * 1.15
    mix = np.tanh(mix * 1.1) * 0.95
    out = (mix.T * 32767).astype(np.int16)
    with wave.open(os.path.join(HERE, "mix.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
    print("audio done", T)

if __name__ == "__main__":
    main()
