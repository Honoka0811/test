# -*- coding: utf-8 -*-
"""自作BGMと効果音を numpy だけで合成する(外部音源なし=権利フリー)。

BGM: 128BPM・Aマイナーのポップなビート(Am-F-C-G)。キック/クラップ/ハイハット/サブベース/
マリンバ風プラックのリード。#1 の直前にライザー(スネアロール+上昇ノイズ)→ドロップ。
効果音: 場面転換のウーシュ、数字スラムのブーム、心拍、ガラスのチャイム、グリッチ、字幕ポップ。
"""
import numpy as np

SR = 48000
BPM = 128
BEAT = 60 / BPM
rng = np.random.default_rng(7)


def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def add(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    j = min(len(buf), i + len(x))
    buf[max(i, 0):j] += g * x[max(0, -i):j - i]


def note(m):
    return 440 * 2 ** ((m - 69) / 12)


# ---------- instruments ----------
def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    x[:200] += rng.normal(0, 0.4, 200) * np.linspace(1, 0, 200)
    return np.tanh(x * 1.6)


def clap():
    n = int(0.3 * SR); t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    e = np.exp(-t * 18) + 0.6 * sum(np.exp(-np.maximum(t - d, 0) * 60) * (t >= d) for d in (0.008, 0.017))
    x = np.convolve(x, np.ones(6) / 6, 'same') - np.convolve(x, np.ones(40) / 40, 'same')
    return x * e * 0.9


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR); t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    x = x - np.convolve(x, np.ones(4) / 4, 'same')
    return x * np.exp(-t * (14 if open_ else 70)) * 0.5


def pluck(freq, dur=0.35, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.35 * bright * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t * 30)
         + 0.2 * np.sin(2 * np.pi * freq * 2 * t))
    return x * env(n, 0.002, 0.16)


def bass(freq, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.3 * np.tanh(3 * np.sin(2 * np.pi * freq * t))
    e = np.minimum(1, t / 0.005) * np.minimum(1, (dur - t) / 0.03)
    return x * e * 0.55


def pad(freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.3 * t) * 0.5) + 0.5 * np.sin(2 * np.pi * f * 1.004 * t) for f in freqs)
    e = np.minimum(1, t / 0.08) * np.minimum(1, (dur - t) / 0.1)
    return x * e / len(freqs) * 0.25


CHORDS = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [67, 72, 76]), (55, [67, 71, 74])]  # Am F C G
MELODY = [76, 0, 72, 74, 76, 79, 76, 72, 77, 0, 76, 72, 69, 72, 74, 0,
          79, 0, 76, 79, 81, 79, 76, 74, 74, 0, 71, 74, 79, 0, 74, 71]


def generate(total, drop_at=None, quiet=None):
    """total 秒の BGM。drop_at: ライザー→ドロップの時刻。quiet: (s,e) リスト=ドラムを抜く区間。"""
    buf = np.zeros(int(total * SR) + SR, dtype=np.float32)
    K, CL, H, HO = kick(), clap(), hat(), hat(True)
    nb = int(total / BEAT) + 1
    for b in range(nb):
        t = b * BEAT
        bar, bi = divmod(b, 4)
        root, ch = CHORDS[bar % 4]
        in_riser = drop_at and drop_at - 4 * BEAT <= t < drop_at
        quiet_now = quiet and any(s <= t < e for s, e in quiet)
        if bi == 0:
            add(buf, pad([note(m) for m in ch], 4 * BEAT), t, 0.9)
        if not in_riser and not quiet_now:
            add(buf, K, t, 0.9)
            if bi in (1, 3):
                add(buf, CL, t, 0.5)
            for s in range(4):
                add(buf, HO if s == 2 else H, t + s * BEAT / 4, 0.35 if s == 2 else 0.22)
            # syncopated bass
            for off, d in ((0, 0.45), (0.75, 0.2), (1.5 - 1, 0)):
                if d:
                    add(buf, bass(note(root - 12), d * BEAT * 2), t + off * BEAT, 0.8)
        # lead (8th notes)
        for h in range(2):
            m = MELODY[(b * 2 + h) % len(MELODY)]
            if m and not quiet_now:
                add(buf, pluck(note(m), 0.3), t + h * BEAT / 2, 0.32 if not in_riser else 0.18)
    if drop_at:
        # snare roll + rising noise sweep
        r0 = drop_at - 4 * BEAT
        n = 32
        for i in range(n):
            tt = r0 + 4 * BEAT * (1 - (1 - i / n) ** 1.6)
            add(buf, CL, tt, 0.15 + 0.4 * i / n)
        ln = int(4 * BEAT * SR); tt = np.arange(ln) / SR
        nz = rng.normal(0, 1, ln)
        sweep = np.zeros(ln); a = 0.0
        cut = np.linspace(0.02, 0.6, ln) ** 2
        for i in range(ln):
            a += cut[i] * (nz[i] - a); sweep[i] = a
        add(buf, sweep * (tt / tt[-1]) ** 2 * 0.6, r0)
    # gentle limiter
    buf = np.tanh(buf * 1.1) * 0.8
    return buf[:int(total * SR)]


# ---------- SFX ----------
def whoosh(d=0.45, up=True):
    n = int(d * SR); t = np.arange(n) / SR
    nz = rng.normal(0, 1, n)
    cut = (np.sin(np.pi * t / d) ** 2) * 0.35 + 0.02
    y = np.zeros(n); a = 0.0
    for i in range(n):
        a += cut[i] * (nz[i] - a); y[i] = a
    return y * np.sin(np.pi * t / d) ** 1.5 * 1.1


def boom():
    n = int(1.2 * SR); t = np.arange(n) / SR
    f = 38 + 90 * np.exp(-t * 10)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    nz = rng.normal(0, 1, n); nz = np.convolve(nz, np.ones(30) / 30, 'same')
    return np.tanh(1.8 * (x + nz * np.exp(-t * 14) * 2)) * 0.9


def heartbeat():
    n = int(0.6 * SR); t = np.arange(n) / SR
    def thump(t0, g):
        tt = np.maximum(t - t0, 0)
        return g * np.sin(2 * np.pi * (50 + 40 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 16) * (t >= t0)
    return np.tanh(2 * (thump(0, 1) + thump(0.2, 0.7)))


def chime(freq=1318.5):
    n = int(0.8 * SR); t = np.arange(n) / SR
    return sum(g * np.sin(2 * np.pi * freq * k * t) * np.exp(-t * (5 + 3 * k)) for k, g in ((1, 1), (2.01, .4), (3.03, .2))) * 0.45


def pop():
    n = int(0.07 * SR); t = np.arange(n) / SR
    f = 900 * np.exp(-t * 30) + 300
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 60) * 0.5


def glitch():
    n = int(0.5 * SR)
    x = np.zeros(n)
    for i in range(0, n, 1200):
        f = rng.choice([220, 440, 880, 1760, 3520])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(1200) / SR)) * rng.choice([0, 0.3, 0.6])
        x[i:i + 1200] = seg[:len(x[i:i + 1200])]
    x += rng.normal(0, 0.15, n)
    return x * np.linspace(1, 0.2, n) * 0.55


def flatline():
    n = int(1.0 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 1000 * t) * np.minimum(1, t / 0.01) * np.minimum(1, (1 - t) / 0.2) * 0.18


if __name__ == '__main__':
    import sys, wave
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    x = generate(total)
    with wave.open(sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
