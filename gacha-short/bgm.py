"""軽快なオリジナルBGMを numpy で合成する(素材不使用・著作権フリー)。"""
import numpy as np, wave, json

SR = 48000
BPM = 124
beat = 60 / BPM
total = json.load(open("build/timings.json"))["total"]
n = int(SR * (total + 0.5))
L = np.zeros(n); R = np.zeros(n)
rng = np.random.default_rng(7)

def hz(m): return 440 * 2 ** ((m - 69) / 12)

def add(buf_l, buf_r, t0, sig, pan=0.0):
    i = int(t0 * SR)
    if i >= n: return
    sig = sig[: n - i]
    buf_l[i:i + len(sig)] += sig * (1 - pan) / 2 * 2 ** 0.5
    buf_r[i:i + len(sig)] += sig * (1 + pan) / 2 * 2 ** 0.5

def env(length, a=0.005, d=0.25, s=0.0):
    t = np.arange(int(length * SR)) / SR
    e = np.minimum(t / a, 1) * (s + (1 - s) * np.exp(-t / d))
    e[-200:] *= np.linspace(1, 0, 200)
    return t, e

def pluck(m, length, vol=0.2):          # 丸い鉄琴っぽい音
    t, e = env(length, 0.003, 0.22)
    f = hz(m)
    return vol * e * (np.sin(2*np.pi*f*t) + 0.35*np.sin(2*np.pi*2*f*t)*np.exp(-t/0.08) + 0.12*np.sin(2*np.pi*4*f*t)*np.exp(-t/0.04))

def pad(m, length, vol=0.05):           # やわらかいコード
    t = np.arange(int(length * SR)) / SR
    f = hz(m)
    e = np.minimum(t / 0.08, 1) * np.minimum((length - t) / 0.12, 1).clip(0)
    return vol * e * (np.sin(2*np.pi*f*t) + 0.3*np.sin(2*np.pi*f*1.005*t) + 0.2*np.sin(2*np.pi*2*f*t))

def bass(m, length, vol=0.22):
    t, e = env(length, 0.005, 0.35, 0.2)
    f = hz(m)
    return vol * e * np.tanh(1.6*np.sin(2*np.pi*f*t) + 0.4*np.sin(2*np.pi*2*f*t))

def kick(vol=0.5):
    t = np.arange(int(0.22 * SR)) / SR
    return vol * np.sin(2*np.pi*(48*t + 70*0.045*(1-np.exp(-t/0.045)))) * np.exp(-t/0.09)

def hat(vol=0.05, d=0.025):
    t = np.arange(int(0.08 * SR)) / SR
    x = rng.standard_normal(len(t)); x = np.diff(x, prepend=0)
    return vol * x * np.exp(-t/d)

def clap(vol=0.12):
    t = np.arange(int(0.16 * SR)) / SR
    x = rng.standard_normal(len(t)); x = x - np.convolve(x, np.ones(12)/12, "same")
    return vol * x * np.exp(-t/0.05)

# コード進行: F - G - Em - Am (明るめの定番進行) / 1小節ずつ
PROG = [
    (41, [65, 69, 72, 76]),   # Fmaj7
    (43, [67, 71, 74, 79]),   # G
    (40, [64, 67, 71, 74]),   # Em7
    (45, [69, 72, 76, 79]),   # Am7
]
ARP = [0, 2, 1, 3, 2, 1, 3, 2]           # 8分のアルペジオ
MEL = [                                   # 2拍ごとのメロディ断片(コード音のindex, オクターブ)
    [(3, 12), None, (2, 12), (1, 12)], [(2, 12), None, (3, 12), None],
    [(1, 12), (2, 12), None, (3, 12)], [(2, 12), None, (0, 24), None],
]
bar = 4 * beat
nbars = int(np.ceil((total + 0.5) / bar))
for b in range(nbars):
    t0 = b * bar
    root, chord = PROG[b % 4]
    intro = b < 2
    for m in chord[:3]:
        add(L, R, t0, pad(m - 12, bar), pan=0.0)
    for k in range(8):
        tt = t0 + k * beat / 2 + (0.012 if k % 2 else 0)      # 軽いスウィング
        add(L, R, tt, pluck(chord[ARP[k]], beat * 0.9, 0.13), pan=-0.35 if k % 2 else 0.35)
    if not intro:
        for k, pat in enumerate([0, 1.5, 2, 3.5]):
            add(L, R, t0 + pat * beat, bass(root - (12 if k % 2 == 0 else 0) + 12, beat * 0.8))
        for k in range(4):
            add(L, R, t0 + k * beat, kick(0.42))
            add(L, R, t0 + (k + 0.5) * beat, hat(0.06, 0.04), pan=0.2)
            add(L, R, t0 + k * beat, hat(0.03), pan=-0.2)
        add(L, R, t0 + 1 * beat, clap()); add(L, R, t0 + 3 * beat, clap())
        for k, note in enumerate(MEL[b % 4]):
            if note:
                add(L, R, t0 + k * beat, pluck(chord[note[0]] + note[1], beat * 1.4, 0.10), pan=0.1)

mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.1)
fade = int(1.6 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
mix[: int(0.02*SR)] *= np.linspace(0, 1, int(0.02*SR))[:, None]
mix = mix / np.abs(mix).max() * 0.85
with wave.open("build/bgm.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
