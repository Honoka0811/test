"""BGM（オリジナル・数値合成）と効果音を生成し、ナレーションとミックスする"""
import json, wave, numpy as np
SR = 48000
tl = json.load(open("build/timeline.json"))
S = {s["id"]: s for s in tl["scenes"]}
TOTAL = tl["total"]
N = int(TOTAL * SR)
rng = np.random.default_rng(1)

def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)

def saw(f, n):
    t = np.arange(n) / SR
    return 2 * ((t * f) % 1) - 1

def lowpass(x, k):
    # 単純な1極ローパス（k: 0..1）
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc); y[i] = acc
    return y

def put(buf, x, t):
    i = int(t * SR)
    if i >= len(buf): return
    x = x[: len(buf) - i]; buf[i:i + len(x)] += x

# ---------- BGM ----------
BPM = 128; beat = 60 / BPM; bar = beat * 4
bgm = np.zeros(N)
drop_off, drop_on = S["drum"]["start"] - 0.2, S["r1"]["start"]
note = lambda m: 440 * 2 ** ((m - 69) / 12)
prog = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [67, 72, 76]), (55, [67, 71, 74])]  # Am F C G

kick_n = int(0.35 * SR); tk = np.arange(kick_n) / SR
kick = np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-tk * 30)) / SR) * env(kick_n, 0.001, 0.12)
hat = lowpass(rng.standard_normal(int(0.06 * SR)), 0.9); hat = (rng.standard_normal(len(hat)) - hat) * env(len(hat), 0.0005, 0.015)
clap = rng.standard_normal(int(0.2 * SR)) * env(int(0.2 * SR), 0.001, 0.05)

t = 0.0; bi = 0
while t < TOTAL - 0.5:
    root, chord = prog[(bi // 1) % 4]
    for b in range(4):
        bt = t + b * beat
        silent = drop_off <= bt < drop_on
        intro_sparse = bt < S["intro"]["start"]
        if not silent:
            put(bgm, 0.9 * kick, bt)
            if not intro_sparse and b in (1, 3): put(bgm, 0.25 * clap, bt)
            put(bgm, 0.12 * hat, bt + beat / 2)
            # オフビートのベース
            bn = int(beat / 2 * SR)
            bass = lowpass(saw(note(root - 12), bn), 0.08) * env(bn, 0.003, 0.12)
            put(bgm, 0.35 * bass, bt + beat / 2)
            # プラック・アルペジオ（16分）
            if not intro_sparse:
                for s in range(4):
                    pn = int(0.18 * SR)
                    f = note(chord[(b * 4 + s) % 3] + (12 if s == 3 else 0))
                    pl = (saw(f, pn) + saw(f * 1.006, pn)) * 0.5
                    put(bgm, 0.07 * lowpass(pl, 0.25) * env(pn, 0.002, 0.06), bt + s * beat / 4)
    # パッド
    pn = int(bar * SR)
    pad = sum(saw(note(m), pn) + saw(note(m) * 1.004, pn) for m in chord) / 6
    padenv = np.minimum(np.arange(pn) / (0.3 * SR), 1) * np.minimum((pn - np.arange(pn)) / (0.2 * SR), 1)
    vol = 0.05 if drop_off <= t < drop_on else 0.07
    put(bgm, vol * lowpass(pad, 0.04) * padenv, t)
    t += bar; bi += 1

# ---------- 効果音 ----------
sfx = np.zeros(N)
def whoosh(dur=0.45):
    n = int(dur * SR); x = rng.standard_normal(n)
    k = np.linspace(0.02, 0.5, n) ** 2
    y = np.empty(n); acc = 0
    for i in range(n): acc += k[i] * (x[i] - acc); y[i] = acc
    return y * np.sin(np.linspace(0, np.pi, n)) ** 2
def impact():
    n = int(0.6 * SR); tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(40 + 160 * np.exp(-tt * 18)) / SR) * env(n, 0.001, 0.25)
    return boom + 0.3 * rng.standard_normal(n) * env(n, 0.001, 0.04)
def ding(f=1318):
    n = int(0.8 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.01 * tt)) * env(n, 0.002, 0.25)
def pop():
    n = int(0.12 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(300 + 900 * tt / 0.12) / SR) * env(n, 0.001, 0.04)

put(sfx, 0.8 * impact(), 0.25)
put(sfx, 0.5 * ding(1760), S["hook2"]["start"])
for r in ["r5", "r4", "r3", "r2"]:
    st = S[r]["start"]
    put(sfx, 0.35 * whoosh(), st - 0.35)
    put(sfx, 0.6 * impact(), st)
    put(sfx, 0.25 * ding(), st + 0.05)
# ドラムロール → シンバル
d0, d1 = S["drum"]["start"], S["r1"]["start"]
t = d0
while t < d1 - 0.05:
    p = (t - d0) / (d1 - d0)
    n = int(0.05 * SR)
    put(sfx, (0.15 + 0.35 * p) * rng.standard_normal(n) * env(n, 0.001, 0.02), t)
    t += 0.09 - 0.05 * p
rn = int((d1 - d0) * SR)
put(sfx, 0.12 * saw(1, 1)[0] * 0 + 0.12 * np.sin(2 * np.pi * np.cumsum(np.linspace(200, 1200, rn)) / SR) * np.linspace(0, 1, rn), d0)
cn = int(2.5 * SR)
crash = lowpass(rng.standard_normal(cn), 0.6); crash = (rng.standard_normal(cn) - crash) * env(cn, 0.001, 0.7)
put(sfx, 0.35 * crash + 0, d1)
put(sfx, 1.0 * impact(), d1)
put(sfx, 0.4 * ding(2093), d1 + 0.05)
for i, off in enumerate([1.6, 3.2, 4.8]):
    put(sfx, 0.4 * pop(), S["tips"]["start"] + off * S["tips"]["dur"] / 6.2)
put(sfx, 0.35 * whoosh(), S["tips"]["start"] - 0.35)
put(sfx, 0.5 * ding(1568), S["cta"]["start"])

# ---------- ナレーション ----------
voice = np.zeros(N)
for s in tl["scenes"]:
    with wave.open(f"build/{s['id']}.wav") as w:
        assert w.getframerate() == SR
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
        if w.getnchannels() == 2: x = x[::2]
    put(voice, x, s["start"])

# サイドチェイン（声が出ている間はBGMを下げる）
venv = np.abs(voice)
win = int(0.15 * SR)
venv = np.convolve(venv, np.ones(win) / win, mode="same")
duck = 1 - 0.55 * np.clip(venv / 0.03, 0, 1)
fade = np.minimum(1, (N - np.arange(N)) / (1.2 * SR))
mix = bgm * 0.55 * duck * fade + sfx * 0.7 + voice * 1.25
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
with wave.open("build/mix.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("ok", TOTAL)
