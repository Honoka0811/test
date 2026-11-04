"""Calmer BGM + gentle SFX (all synthesized here). Writes mix_soft.wav."""
import numpy as np, wave, os
from audio import SR, t_arr, lp, hp, bp, place, read_wav, note, rng
from timeline import build, VOICE, HERE

BPM = 88
BEAT = 60 / BPM
STEP = BEAT / 2  # 8th notes

def epiano(f, d=1.6, g=1.0):
    """Soft FM electric-piano-like tone."""
    t = t_arr(d)
    mod = np.sin(2 * np.pi * f * 2 * t) * 1.2 * np.exp(-t / 0.25)
    x = np.sin(2 * np.pi * f * t + mod)
    env = np.minimum(1, t / 0.008) * np.exp(-t / 0.7)
    return lp(x * env, 2500) * 0.09 * g

def pad(freqs, d):
    t = t_arr(d)
    x = sum(np.sin(2 * np.pi * f * dt * t) for f in freqs for dt in (0.998, 1.002))
    x = x / (len(freqs) * 2)
    env = np.minimum(1, t / 0.8) * np.minimum(1, (d - t) / 0.8)
    return x * env * 0.10

def sub(f, d):
    t = t_arr(d)
    env = np.minimum(1, t / 0.03) * np.minimum(1, (d - t) / 0.1)
    return np.sin(2 * np.pi * f * t) * env * 0.16

def soft_kick():
    t = t_arr(0.3)
    f = 50 + 40 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12) * 0.28

def shaker():
    t = t_arr(0.08)
    return hp(rng.standard_normal(len(t)), 6000) * np.exp(-t / 0.02) * 0.035

def pop():  # pin drop: gentle wooden blip
    t = t_arr(0.18)
    f = 900 * np.exp(-t / 0.05) + 500
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05) * 0.18

def soft_whoosh(d=0.5):
    t = t_arr(d)
    n = lp(rng.standard_normal(len(t)), 1800)
    return n * np.sin(np.pi * t / d) ** 2 * 0.06

def chime(freqs, gap=0.09, g=1.0):
    out = np.zeros(int((gap * len(freqs) + 2.0) * SR))
    for i, f in enumerate(freqs):
        t = t_arr(2.0)
        x = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t / 0.2)) * np.exp(-t / 0.8)
        j = int(i * gap * SR); out[j:j + len(x)] += x * 0.08 * g
    return out

def swell(d):
    t = t_arr(d)
    fs = [note(n) for n in (57, 64, 69)]
    x = sum(np.sin(2 * np.pi * f * t * (1 + 0.02 * t / d)) for f in fs) / 3
    return x * (t / d) ** 2 * 0.12

CHORDS = [(45, [57, 60, 64, 67]), (41, [53, 57, 60, 64]), (48, [55, 60, 64, 71]), (43, [55, 59, 62, 67])]  # Am7 Fmaj7 Cmaj7 G

def main():
    scenes, total = build()
    T = total + 0.5; N = int(T * SR)
    music = np.zeros((2, N)); sfx = np.zeros((2, N)); voice = np.zeros((2, N))
    S = {s["key"]: s for s in scenes}

    def level(t):
        for s in scenes:
            if s["start"] <= t < s["end"]:
                k = s["key"]
                if k == "tease": return 0.0
                if k in ("hook", "extra", "kara", "nanyo", "hoppo"): return 0.6
                return 1.0
        return 0.0

    K, SH = soft_kick(), shaker()
    cache = {}
    def cget(k, fn):
        if k not in cache: cache[k] = fn()
        return cache[k]
    bar_len = BEAT * 4
    nsteps = int(T / STEP)
    for i in range(nsteps):
        t = i * STEP; lv = level(t)
        if lv == 0: continue
        bar = i // 8; st = i % 8
        root, tones = CHORDS[bar % 4]
        if st == 0:
            place(music, cget(("pad", bar % 4), lambda: pad([note(x) for x in tones], bar_len)), t, lv)
            place(music, cget(("sub", root), lambda: sub(note(root), bar_len * 0.95)), t, lv)
        # gentle broken-chord e-piano
        pat = [0, 2, 1, 3, 2, 1, 3, 2]
        n_ = tones[pat[st]] + (12 if st in (3, 6) else 0)
        place(music, cget(("ep", n_), lambda: epiano(note(n_))), t, lv * (1.0 if st % 2 == 0 else 0.7), -0.3 if st % 2 else 0.3)
        if lv >= 1.0:
            if st in (0, 4): place(music, K, t, 0.8)
            place(music, SH, t, 0.8 if st % 2 else 0.5, 0.4)

    # SFX
    place(sfx, chime([note(n) for n in (69, 72, 76, 81)]), S["title"]["start"], 1.0)
    for s in scenes:
        k = s["key"]
        if k.startswith("r") and k[1:].isdigit():
            place(sfx, soft_whoosh(), s["start"] - 0.25, 1.0)
            if k != "r1": place(sfx, pop(), s["start"] + 0.5 + 0.35, 1.0)
        if k in ("extra", "kara", "nanyo", "hoppo", "outro"):
            place(sfx, soft_whoosh(0.45), s["start"] - 0.2, 0.8)
    for k, n in (("kara", 1), ("nanyo", 2), ("hoppo", 3)):
        for j in range(n): place(sfx, pop(), S[k]["start"] + 0.6 + j * 0.25 + 0.35, 0.9)
    te, r1 = S["tease"], S["r1"]
    place(sfx, swell(te["end"] - te["start"]), te["start"], 1.0)
    place(sfx, chime([note(n) for n in (72, 76, 79, 84, 88)], 0.07, 1.3), r1["start"], 1.0)

    for s in scenes:
        place(voice, read_wav(os.path.join(VOICE, s["key"] + ".wav")), s["vstart"], 1.0)

    env = lp(np.abs(voice[0]), 5); env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    music *= (1 - 0.6 * env)
    fade = np.ones(N); fl = int(2.0 * SR); fade[-fl:] = np.linspace(1, 0, fl); music *= fade
    fi = int(1.0 * SR); music[:, :fi] *= np.linspace(0, 1, fi)
    mix = music * 0.32 + sfx * 0.5 + voice * 1.1
    peak = np.abs(mix).max(); mix = mix / peak * 0.89
    with wave.open(os.path.join(HERE, "mix_soft.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix.T * 32767).astype(np.int16).tobytes())
    print("done", T)

if __name__ == "__main__":
    main()
