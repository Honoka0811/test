# -*- coding: utf-8 -*-
"""ライセンスフリーのBGMを numpy で合成する（アップテンポなローファイ風ループ）。
使い方: python3 make_bgm.py <seconds> <out.wav>
"""
import sys, math
import numpy as np
import wave

SR = 44100
BPM = 112
BEAT = 60.0 / BPM

def note_hz(semi):  # semitone offset from A4
    return 440.0 * 2 ** (semi / 12.0)

def env(n, a=0.01, d=0.3, s=0.6, r=0.1):
    t = np.arange(n) / SR
    length = n / SR
    e = np.ones(n) * s
    ai = int(a * SR); di = int(d * SR); ri = int(r * SR)
    if ai > 0: e[:ai] = np.linspace(0, 1, ai)
    if di > 0: e[ai:ai + di] = np.linspace(1, s, min(di, max(0, n - ai)))
    if ri > 0 and ri < n: e[-ri:] *= np.linspace(1, 0, ri)
    return e

def osc(freq, n, kind="saw"):
    t = np.arange(n) / SR
    if kind == "sine": return np.sin(2 * np.pi * freq * t)
    if kind == "tri": return 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    if kind == "square": return np.sign(np.sin(2 * np.pi * freq * t)) * 0.6
    return 2 * ((t * freq) % 1) - 1  # saw

def lowpass(x, cutoff):
    # simple one-pole lowpass
    rc = 1.0 / (2 * np.pi * cutoff); dt = 1.0 / SR; a = dt / (rc + dt)
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y

def lowpass_fast(x, cutoff):
    from numpy import convolve
    k = int(SR / cutoff) | 1
    win = np.hanning(k); win /= win.sum()
    return np.convolve(x, win, mode="same")

# Chord progression (relative semitones to A4): Fmaj7 - G - Am7 - C   (upbeat / bright)
CHORDS = [
    [-16, -9, -4, 3],    # F  A  C  E   (Fmaj7)
    [-14, -10, -5, 2],   # G  B  D  F#? -> use G B D G: 
    [-12, -9, -5, 0],    # A  C  E  G  (Am7)
    [-9, -5, -2, 3],     # C  E  G  C
]
CHORDS[1] = [-14, -10, -5, -2]  # G B D G
BASS = [-28, -26, -24, -21]      # F G A C (two octaves down)

def render(seconds):
    n_total = int(seconds * SR)
    out = np.zeros(n_total)
    bar = BEAT * 4
    n_bars = int(math.ceil(seconds / bar)) + 1
    rng = np.random.default_rng(7)
    for b in range(n_bars):
        start = int(b * bar * SR)
        chord = CHORDS[b % 4]
        nb = int(bar * SR)
        # pad chord (soft saw + tri, lowpassed)
        pad = np.zeros(nb)
        for s in chord:
            f = note_hz(s)
            pad += 0.5 * osc(f, nb, "saw") + 0.5 * osc(f * 1.003, nb, "tri")
        pad = lowpass_fast(pad, 1800) * env(nb, 0.05, 0.8, 0.5, 0.3) * 0.08
        # bass: 8th notes pattern
        bass = np.zeros(nb)
        pat = [1, 0, 1, 1, 0, 1, 0, 1]
        for i, on in enumerate(pat):
            if not on: continue
            s0 = int(i * BEAT / 2 * SR); ln = int(BEAT / 2 * SR * 0.9)
            seg = osc(note_hz(BASS[b % 4]), ln, "sine") * 0.7 + osc(note_hz(BASS[b % 4]), ln, "square") * 0.15
            seg *= env(ln, 0.005, 0.15, 0.5, 0.05)
            bass[s0:s0 + ln] += seg[:min(ln, nb - s0)]
        bass *= 0.22
        # arpeggio pluck (16th), bright
        arp = np.zeros(nb)
        for i in range(16):
            s0 = int(i * BEAT / 4 * SR); ln = int(BEAT / 4 * SR * 0.95)
            s = chord[(i * 2 + (i // 4)) % 4] + 12
            seg = osc(note_hz(s), ln, "tri") * env(ln, 0.002, 0.12, 0.2, 0.03)
            arp[s0:s0 + ln] += seg[:min(ln, nb - s0)]
        arp = lowpass_fast(arp, 4000) * 0.10
        # drums
        drums = np.zeros(nb)
        for i in range(8):  # kick on 1 and 3, plus pickup
            if i in (0, 4, 7):
                s0 = int(i * BEAT / 2 * SR); ln = int(0.18 * SR)
                t = np.arange(ln) / SR
                k = np.sin(2 * np.pi * (50 + 80 * np.exp(-t * 30)) * t) * np.exp(-t * 18)
                drums[s0:s0 + ln] += k[:min(ln, nb - s0)] * 0.55
        for i in range(8):  # snare/clap on 2 and 4
            if i in (2, 6):
                s0 = int(i * BEAT / 2 * SR); ln = int(0.12 * SR)
                t = np.arange(ln) / SR
                sn = rng.standard_normal(ln) * np.exp(-t * 35)
                drums[s0:s0 + ln] += lowpass_fast(sn, 6000)[:min(ln, nb - s0)] * 0.25
        for i in range(16):  # hats on 8ths with off-beat accent
            s0 = int(i * BEAT / 4 * SR); ln = int(0.03 * SR)
            if i % 2 == 0 or rng.random() < 0.5:
                t = np.arange(ln) / SR
                h = rng.standard_normal(ln) * np.exp(-t * 90)
                h = h - lowpass_fast(h, 5000)  # crude highpass
                drums[s0:s0 + ln] += h[:min(ln, nb - s0)] * (0.09 if i % 4 == 2 else 0.06)
        mix = pad + bass + arp + drums
        if start >= n_total: break
        end = min(start + nb, n_total)
        out[start:end] += mix[:end - start]
    # gentle master: soft clip + normalize
    out = np.tanh(out * 1.6)
    out /= (np.max(np.abs(out)) + 1e-9)
    out *= 0.9
    # fades
    fi = int(1.5 * SR); fo = int(3.0 * SR)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-fo:] *= np.linspace(1, 0, fo)
    return out

def save(x, path):
    stereo = np.stack([x, x], axis=1)
    pcm = (stereo * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

if __name__ == "__main__":
    sec = float(sys.argv[1]); out = sys.argv[2]
    save(render(sec), out)
    print("bgm written", out, sec, "sec")
