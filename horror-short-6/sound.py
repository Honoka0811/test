# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(79)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tt(d): return np.arange(int(d * SR)) / SR
def add(buf, t0, sig, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf) or i < 0: return
    e = min(i + len(sig), len(buf)); buf[i:e] += sig[:e - i] * g
def lowpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / fc) ** 4), len(x)).astype(np.float32)
def highpass(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * (f / fc) ** 4 / (1 + (f / fc) ** 4), len(x)).astype(np.float32)
def conv(x, ir):
    n = len(x) + len(ir) - 1; m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)].astype(np.float32)
def reverb_ir(sec, seed, fc=5000):
    r = np.random.default_rng(seed); t = tt(sec)
    ir = lowpass(r.standard_normal(len(t)).astype(np.float32), fc) * np.exp(-t * 6.9 / sec)
    return ir / np.sqrt(np.sum(ir ** 2))
def ramp(t0, t1, v0=0.0, v1=1.0):
    t = np.arange(N) / SR
    return (v0 + (v1 - v0) * np.clip((t - t0) / max(t1 - t0, 1e-6), 0, 1)).astype(np.float32)

NIGHTS = [L['l5']['start'] + 0.4 + 1.15 * k for k in range(3)]
T_LAST = L['l7']['start'] - 0.05
MATH = dict(a=L['l8']['start'] + 0.2, b=L['l8']['start'] + 1.6, eq=L['l9']['start'] + 0.75)
HIT = L['now']['end'] + 0.5
EV = dict(t_me=L['l1']['start'] - 0.25, t_notif=L['l2']['start'] - 0.2, t_val=L['l3']['start'] + 1.3, t_cmp=L['l4']['start'] + 0.2, t_list=L['l5']['start'] - 0.25,
          nights=NIGHTS, t_lastrow=L['l6']['start'] + 0.2, t_last=T_LAST, t_math=L['l8']['start'] - 0.25, math=MATH, t_carry=L['l10']['start'] - 0.25, hit=HIT)

def pad():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(23), 1.0), (midi(23) * 1.006, 0.8), (midi(35), 0.45), (midi(42), 0.18), (midi(38), 0.14), (midi(36), 0.06)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.08 * t)).astype(np.float32)
    return (x * 0.11 + lowpass(rng.standard_normal(N).astype(np.float32), 90) * 0.5).astype(np.float32)
def piano(f, dur=5.0):
    t = tt(dur); x = np.zeros(len(t), np.float32)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k); x += (np.sin(2 * np.pi * fk * t) * np.exp(-t * (0.7 + 0.45 * k)) / k ** 1.3).astype(np.float32)
    x[:144] *= np.linspace(0, 1, 144); return x
def keys():
    """Bマイナーの、同じ3音を繰り返すピアノ(毎晩くり返される記録のイメージ)"""
    x = np.zeros(N, np.float32); seq = [59, 62, 66, 65, 59, 62, 66, 67, 59, 62, 66, 65, 58, 62, 65, 64]; t0 = 1.0; i = 0
    while t0 < HIT - 2.5:
        add(x, t0, piano(midi(seq[i % 16])), 0.15)
        if i % 4 == 0: add(x, t0, piano(midi(seq[i % 16] - 24), 6.0), 0.2)
        t0 += 0.92; i += 1
    return x
def strings():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32); a, b = L['l8']['start'], HIT
    prog = np.clip((t - a) / (b - a), 0, 1)
    for k, n in enumerate([71, 72, 77, 78, 83, 84.5, 89]):
        f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
    env = ramp(L['l3']['start'], a, 0, 0.12) + ramp(a, b, 0, 0.9) ** 2 * 0.9
    return lowpass(x, 5200) * env * (1 - ramp(b - 0.05, b + 0.1)) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = L['l6']['start']; t0 = a
    while t0 < HIT - 0.3:
        p = np.clip((t0 - a) / (HIT - a), 0, 1); g = 0.35 + 0.65 * p
        add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g); t0 += 0.95 - 0.4 * p
    return x * 0.5
def clunk():
    """つまみが回って、かんぬきが動く「カチャン」"""
    x = np.zeros(int(0.6 * SR), np.float32)
    for dt, f, g in [(0, 2300, 0.7), (0.05, 1500, 0.5)]:
        t = tt(0.07); add(x, dt, (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.6 * t)) * np.exp(-t * 80) * g + highpass(rng.standard_normal(len(t)).astype(np.float32), 2500) * np.exp(-t * 130) * 0.5)
    t = tt(0.4); add(x, 0.13, (np.sin(2 * np.pi * 130 * t) * np.exp(-t * 26) + 0.6 * np.sin(2 * np.pi * 410 * t) * np.exp(-t * 45) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 2500) * np.exp(-t * 70) * 1.5))
    return x
def creak(d=1.1, f0=380):
    t = tt(d); f = f0 * (1 + 0.5 * (t / d) ** 2) * (1 + 0.03 * np.sin(2 * np.pi * 9 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.6 * np.sin(2.02 * ph) + 0.4 * np.sin(3.1 * ph)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * t)))
    return (x * np.sin(np.pi * t / d) ** 1.2).astype(np.float32)
def thud():
    t = tt(0.5); return (np.sin(2 * np.pi * 85 * t) * np.exp(-t * 18) + 0.5 * np.sin(2 * np.pi * 210 * t) * np.exp(-t * 35) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 1200) * np.exp(-t * 40) * 2).astype(np.float32)
def tick():
    t = tt(0.05); return (np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 120)).astype(np.float32)
def ping():
    x = np.zeros(int(0.7 * SR), np.float32)
    for dt, f in [(0, 1046.5), (0.13, 1568)]:
        t = tt(0.5); add(x, dt, (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 11))
    return x
def buzz(d=0.5):
    t = tt(d); x = np.sign(np.sin(2 * np.pi * 165 * t)) * 0.5 + np.sin(2 * np.pi * 82 * t)
    return lowpass((x * np.sin(np.pi * t / d) ** 0.3).astype(np.float32), 900)
def boom(g=1.0):
    t = tt(3.0); f = 34 + 50 * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 300) * np.exp(-t * 7) * 2.5
    return (x * g).astype(np.float32)
def stinger():
    t = tt(2.4); x = np.zeros(len(t), np.float32)
    for k, n in enumerate([59, 60, 65, 66, 71, 72.5, 77, 84]):
        f = midi(n) * (1 - 0.06 * t / 2.4) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.3 * np.sign(np.sin(ph))).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.7) + highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + boom(0.9)[:len(t)]

def celesta(f, dur=4.0):
    t = tt(dur); x = np.sin(2 * np.pi * f * t) * np.exp(-t * 1.4) + 0.4 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 5) + 0.15 * np.sin(2 * np.pi * 6.3 * f * t) * np.exp(-t * 9)
    x[:96] *= np.linspace(0, 1, 96); return x.astype(np.float32)
def keys():
    """3拍子のゆっくりしたワルツ(Eマイナー)。高音の旋律が少しずつ狂う"""
    x = np.zeros(N, np.float32); bass = [40, 40, 45, 47, 40, 43, 45, 46]; mel = [76, 79, 83, 82, 79, 76, 75, 71]; beat = 0.62; t0 = 0.9; i = 0
    while t0 < HIT - 2.5:
        b = bass[(i // 3) % 8]
        if i % 3 == 0: add(x, t0, piano(midi(b), 5.0), 0.2); add(x, t0, celesta(midi(mel[(i // 3) % 8]) * (1 + rng.uniform(-0.004, 0.004))), 0.13)
        else: add(x, t0, piano(midi(b + 12 + (3 if i % 3 == 1 else 7)), 2.5), 0.07)
        t0 += beat; i += 1
    return x
def beep(f=2000, d=0.12):
    t = tt(d); x = np.sin(2 * np.pi * f * t) * np.minimum(1, np.minimum(t, d - t) * 200); return x.astype(np.float32)
def step():
    t = tt(0.35); return (np.sin(2 * np.pi * 95 * t) * np.exp(-t * 22) + 0.7 * np.sin(2 * np.pi * 260 * t) * np.exp(-t * 40) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 1500) * np.exp(-t * 45) * 2.5).astype(np.float32)

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    hall = [reverb_ir(3.6, 1), reverb_ir(3.6, 2)]; room = [reverb_ir(1.1, 3, 3500), reverb_ir(1.1, 4, 3500)]
    ui = np.zeros(N, np.float32); big = np.zeros(N, np.float32); night = np.zeros(N, np.float32)
    def scale_beep(t0, g=0.16):          # 体重計の「ピピッ」(測定確定)
        add(ui, t0, beep(), g); add(ui, t0 + 0.16, beep(), g)
    scale_beep(0.75); scale_beep(L['l1']['end'] - 1.6, 0.1)
    add(ui, EV['t_notif'] + 0.1, ping(), 0.2); scale_beep(EV['t_val'], 0.14)
    for tn in NIGHTS: add(ui, tn, tick(), 0.22); scale_beep(tn + 0.05, 0.08)
    add(ui, EV['t_lastrow'], tick(), 0.22); scale_beep(T_LAST, 0.2)
    add(ui, MATH['a'], tick(), 0.25); add(ui, MATH['b'], tick(), 0.25); add(ui, MATH['eq'], beep(1320, 0.5), 0.12)
    # 昨夜の音: 床がきしみ、重い足音が体重計まで歩く
    a = L['l10']['start']
    add(night, a + 0.6, creak(1.0, 300), 0.12)
    for k in range(4): add(night, a + 1.7 + 0.62 * k, step(), 0.5 + 0.1 * k)
    add(night, a + 4.5, thud(), 0.5)
    add(big, 0.0, boom(0.7)); add(big, T_LAST, boom(0.8)); add(big, MATH['eq'], boom(0.55)); add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']: add(last if l['id'] == 'now' else nar, l['start'], segs[l['id']])
    hop = SR // 20; rms = np.sqrt(np.mean(nar[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    quiet = 1 - 0.75 * ramp(L['l6']['end'], L['l6']['end'] + 0.2) * (1 - ramp(T_LAST, T_LAST + 0.3)) - 0.6 * ramp(L['l10']['end'], L['l10']['end'] + 0.3) * (1 - ramp(HIT - 0.05, HIT))
    ky = keys(); bedm = pad() * ramp(0, 0.6, 0.35, 1) + strings()
    hb = heartbeat(); out = []
    for ch in range(2):
        music = (bedm + ky * 0.55 + conv(ky, hall[ch]) * 0.5) * quiet * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        fx = big + conv(big, hall[ch]) * 0.2 + hb + ui + conv(ui, room[ch]) * 0.25 + (night + conv(night, room[ch]) * 0.9) * (0.65 if ch == 0 else 1.0)
        out.append(music * duck + fx + nar + conv(nar, room[ch]) * 0.03 + last * (1.0 if ch == 0 else 0.75) + conv(last, hall[ch]) * 0.6)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([(bedm + ky * 0.55 + conv(ky, hall[c]) * 0.5) * 2.5 for c in range(2)], axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
