"""Procedurally generated BGM + SFX (no third-party audio, royalty-free)."""
import numpy as np, wave, sys

SR = 44100


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def env(n, a=0.005, d=0.2, s=0.0, r=0.05, sus_len=None):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0)
    e = e * (s + (1 - s) * np.exp(-np.maximum(t - a, 0) / max(d, 1e-4)))
    return e


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def saw(f, n, detune=(0.0,)):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in detune:
        ph = (t * f * (1 + d)) % 1.0
        out += 2 * ph - 1
    return out / len(detune)


def lowpass(x, cutoff):
    # one-pole, cutoff may be array
    a = np.exp(-2 * np.pi * np.asarray(cutoff) / SR) * np.ones(len(x))
    y = np.zeros_like(x)
    prev = 0.0
    for i in range(len(x)):
        prev = (1 - a[i]) * x[i] + a[i] * prev
        y[i] = prev
    return y


def lp_fast(x, cutoff):
    from scipy.signal import butter, lfilter
    b, a = butter(2, cutoff / (SR / 2))
    return lfilter(b, a, x)


def hp_fast(x, cutoff):
    from scipy.signal import butter, lfilter
    b, a = butter(2, cutoff / (SR / 2), "high")
    return lfilter(b, a, x)


rng = np.random.default_rng(7)


def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 120 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.12) * 1.0 + 0.3 * np.sin(ph) * np.exp(-t / 0.01)


def clap():
    n = int(0.25 * SR); t = np.arange(n) / SR
    nz = rng.uniform(-1, 1, n)
    nz = hp_fast(nz, 900)
    e = np.exp(-t / 0.06)
    for off in (0.0, 0.012, 0.024):
        e += 0.6 * np.exp(-np.maximum(t - off, 0) / 0.006) * (t >= off)
    return nz * e * 0.45


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR); t = np.arange(n) / SR
    nz = hp_fast(rng.uniform(-1, 1, n), 7000)
    return nz * np.exp(-t / (0.06 if open_ else 0.015)) * 0.25


def bgm(total_sec, bpm=124):
    beat = 60 / bpm
    bar = beat * 4
    n_total = int(total_sec * SR) + SR
    L = np.zeros(n_total); R = np.zeros(n_total)
    # I - V - vi - IV in C (bright pop)
    prog = [(48, [60, 64, 67, 72]), (43, [59, 62, 67, 71]), (45, [57, 60, 64, 69]), (41, [57, 60, 65, 69])]
    K, C, H, HO = kick(), clap(), hat(), hat(True)

    def add(buf, x, start, g=1.0):
        s = int(start * SR)
        if s >= len(buf): return
        e = min(len(buf), s + len(x))
        buf[s:e] += x[: e - s] * g

    nbars = int(np.ceil(total_sec / bar)) + 1
    for b in range(nbars):
        t0 = b * bar
        root, chord = prog[b % 4]
        intro = b < 2
        # drums
        for i in range(4):
            bt = t0 + i * beat
            if not intro or i in (0, 2):
                add(L, K, bt, 0.9); add(R, K, bt, 0.9)
            if not intro and i in (1, 3):
                add(L, C, bt, 0.8); add(R, C, bt + 0.004, 0.8)
            for h in range(2):
                ht = bt + h * beat / 2
                hx = HO if h == 1 else H
                g = 0.9 if h == 1 else 0.5
                add(L, hx, ht, g * 0.8); add(R, hx, ht, g)
        # bass: offbeat 8ths pumping
        for i in range(8):
            bt = t0 + i * beat / 2
            n = int(beat / 2 * 0.9 * SR)
            note = root + (12 if i % 2 else 0)
            x = saw(midi(note), n, (0, 0.004))
            x = lp_fast(x, 900) * env(n, 0.003, 0.15, 0.3)
            # sidechain-ish: quieter on downbeats
            g = 0.30 if i % 2 else 0.18
            add(L, x, bt, g); add(R, x, bt, g)
        # chord stabs (syncopated)
        stab_pos = [0.5, 1.5, 2.0, 3.0, 3.5] if not intro else [0.0, 2.0]
        for sp in stab_pos:
            n = int(beat * 0.45 * SR)
            x = np.zeros(n)
            for m in chord:
                x += saw(midi(m), n, (-0.006, 0.0, 0.007))
            x = lp_fast(x / len(chord), 2600 if not intro else 1200) * env(n, 0.004, 0.12, 0.2)
            add(L, x, t0 + sp * beat, 0.16); add(R, x, t0 + sp * beat + 0.008, 0.16)
        # arpeggio pluck (16ths) from bar 4
        if b >= 4:
            arp = chord + [chord[1] + 12, chord[2] + 12]
            pattern = [0, 2, 1, 3, 4, 2, 5, 3]
            for i in range(16):
                m = arp[pattern[i % 8]] + 12
                n = int(beat / 4 * SR)
                t = np.arange(n) / SR
                x = (np.sign(np.sin(2 * np.pi * midi(m) * t)) * 0.5 + np.sin(2 * np.pi * midi(m) * t)) * np.exp(-t / 0.05)
                x = lp_fast(x, 4000)
                pan = 0.5 + 0.35 * np.sin(i * 0.8)
                add(L, x, t0 + i * beat / 4, 0.05 * (1 - pan) * 2); add(R, x, t0 + i * beat / 4, 0.05 * pan * 2)
    mix = np.stack([L, R], 1)[: int(total_sec * SR)]
    # fade in/out
    fi = int(0.3 * SR); fo = int(1.5 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    mix = np.tanh(mix * 1.2) * 0.8
    return mix


# ---------------- SFX ----------------
def sfx_whoosh():
    n = int(0.45 * SR); t = np.arange(n) / SR
    nz = rng.uniform(-1, 1, n)
    from scipy.signal import butter, lfilter
    out = np.zeros(n)
    seg = 512
    for i in range(0, n, seg):
        fc = 400 + 5000 * (i / n) ** 1.5
        b, a = butter(2, [fc / (SR / 2), min(fc * 2.2, SR / 2 - 100) / (SR / 2)], "band")
        out[i:i + seg] = lfilter(b, a, nz[i:i + seg])
    e = np.sin(np.pi * t / t[-1]) ** 2
    return out * e * 0.9


def sfx_impact():
    n = int(0.9 * SR); t = np.arange(n) / SR
    f = 40 + 90 * np.exp(-t / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    boom = np.sin(ph) * np.exp(-t / 0.35)
    nz = lp_fast(rng.uniform(-1, 1, n), 3000) * np.exp(-t / 0.04) * 0.6
    return np.tanh((boom + nz) * 1.8) * 0.9


def sfx_coin():
    n = int(0.6 * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for st, f in ((0.0, 1975.5), (0.08, 2637.0)):
        tt = np.maximum(t - st, 0)
        x += (t >= st) * (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-tt / 0.18)
    return x * 0.35


def sfx_pop():
    n = int(0.15 * SR); t = np.arange(n) / SR
    f = 300 + 900 * (t / t[-1])
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04) * 0.5


def sfx_drumroll(sec=1.6):
    n = int(sec * SR); out = np.zeros(n + SR // 2)
    t_hit = 0.0; i = 0
    while t_hit < sec:
        s = int(t_hit * SR)
        m = int(0.08 * SR); tt = np.arange(m) / SR
        hit = hp_fast(rng.uniform(-1, 1, m), 300) * np.exp(-tt / 0.03)
        hit += np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.03) * 0.5
        g = 0.25 + 0.6 * (t_hit / sec)
        out[s:s + m] += hit * g
        t_hit += 0.05; i += 1
    # cymbal crash at end
    m = int(1.2 * SR); tt = np.arange(m) / SR
    crash = hp_fast(rng.uniform(-1, 1, m), 4000) * np.exp(-tt / 0.4) * 0.5
    s = int(sec * SR)
    out2 = np.zeros(s + m); out2[: len(out)] = out[: s + m] if len(out) <= s + m else out[: s + m]
    out2[s:s + m] += crash
    return out2 * 0.6


def sfx_shock():
    # descending "ええっ" style synth
    n = int(0.7 * SR); t = np.arange(n) / SR
    f = 900 * np.exp(-t / 0.35) + 150
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3
    return lp_fast(x, 3000) * np.exp(-t / 0.3) * 0.6


def sfx_fanfare():
    notes = [(0, 72, 0.12), (0.13, 76, 0.12), (0.26, 79, 0.12), (0.39, 84, 0.6)]
    n = int(1.3 * SR); out = np.zeros(n)
    for st, m, d in notes:
        k = int(d * SR); tt = np.arange(k) / SR
        x = saw(midi(m), k, (-0.005, 0.005)) + 0.5 * saw(midi(m - 12), k)
        x = lp_fast(x, 3500) * env(k, 0.01, d * 2, 0.6) * np.minimum(1, (d - tt) / 0.03 + 0.0).clip(0, 1)
        s = int(st * SR); out[s:s + k] += x
    return out * 0.35


if __name__ == "__main__":
    outdir = sys.argv[1]
    dur = float(sys.argv[2])
    write_wav(f"{outdir}/bgm.wav", bgm(dur))
    for name, fn in [("whoosh", sfx_whoosh), ("impact", sfx_impact), ("coin", sfx_coin), ("pop", sfx_pop),
                     ("drumroll", sfx_drumroll), ("shock", sfx_shock), ("fanfare", sfx_fanfare)]:
        write_wav(f"{outdir}/{name}.wav", fn())
    print("ok")
