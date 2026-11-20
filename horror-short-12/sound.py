# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(181)

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

T_ROOM = L['l1']['start'] - 0.3                 # 夜の部屋(1日目)
T_FACE = L['l1b']['start'] - 0.1                 # すき間の女の人に気づく
T_TAPE = L['l2']['start'] - 0.25                 # ガムテープでとめる
T_N2 = L['l3']['start'] - 0.3                    # 次の夜。テープがはがされ、戸が開いている
T_POINT = L['l3']['start'] + 3.2                 # 上を指さす
T_MORN = L['l4']['start'] - 0.3                  # 朝。はがされたテープ
T_N3 = L['l5']['start'] - 0.3                    # 次の夜。口を動かす
MOUTH = [L['l5']['end'] + 0.35 + 0.6 * k for k in range(3)]   # 「に」「げ」「て」
T_CLOSET = L['l6']['start'] - 0.2                # クローゼットを開けて、天井を照らす
T_OPEN = L['l6']['start'] + 0.9                  # 戸を開ける音
T_LIGHT = L['l6']['start'] + 2.3                 # ライトをつける
T_HATCH = L['l7']['start'] + 0.2                 # 点検口を照らす
T_CREAK = L['l9']['start'] + 1.75                # ギシッ
T_SLIDE = L['now']['start'] - 1.1                # ふたが、ゆっくりずれていく
HIT = L['now']['end'] + 0.5
EV = dict(room=T_ROOM, face=T_FACE, tape=T_TAPE, n2=T_N2, point=T_POINT, morn=T_MORN, n3=T_N3, mouth=MOUTH, closet=T_CLOSET, open=T_OPEN, light=T_LIGHT,
          hatch=T_HATCH, creak=T_CREAK, slide=T_SLIDE, hit=HIT)

def roomtone():
    """夜の部屋: 冷蔵庫の低いうなり、空調のかすかな音、時計の秒針"""
    t = np.arange(N) / SR; x = (np.sin(2 * np.pi * 50 * t) + 0.4 * np.sin(2 * np.pi * 100 * t)).astype(np.float32) * 0.05 + lowpass(rng.standard_normal(N).astype(np.float32), 700) * 0.25
    tk = tt(0.03)
    for k in np.arange(0.5, DUR, 1.0): add(x, k, (np.sin(2 * np.pi * (2400 if int(k) % 2 else 2100) * tk) * np.exp(-tk * 230)).astype(np.float32), 0.35)
    return x
def piano(f, dur=5.0):
    t = tt(dur); x = np.zeros(len(t), np.float32)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k); x += (np.sin(2 * np.pi * fk * t) * np.exp(-t * (0.7 + 0.45 * k)) / k ** 1.3).astype(np.float32)
    x[:144] *= np.linspace(0, 1, 144); return x
def keys():
    """低くまばらなピアノ(Cマイナー)。種明かしの前で止まる"""
    x = np.zeros(N, np.float32); seq = [48, 51, 55, 54, 48, 51, 53, 52, 47, 51, 54, 53, 46, 50, 53, 52]; t0 = 1.2; i = 0
    while t0 < T_HATCH:
        add(x, t0, piano(midi(seq[i % 16])), 0.13)
        if i % 4 == 0: add(x, t0, piano(midi(seq[i % 16] - 12), 6.0), 0.16)
        t0 += 1.8; i += 1
    return x
def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(24), 1.0), (midi(24) * 1.006, 0.8), (midi(36), 0.4), (midi(43), 0.16), (midi(37), 0.08)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    return (x * (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)) * 0.09).astype(np.float32)
def strings():
    t = np.arange(N) / SR
    def cluster(a, b, peak):
        prog = np.clip((t - a) / (b - a), 0, 1); y = np.zeros(N, np.float32)
        for k, n in enumerate([72, 73, 78, 79, 84, 85.5, 90]):
            f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
            y += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
        return y * (ramp(a, b) ** 2 * peak) * (1 - ramp(b - 0.05, b + 0.15))
    return lowpass(cluster(T_FACE, T_TAPE, 0.4) + cluster(T_N3, MOUTH[2] + 0.6, 0.6) + cluster(T_HATCH, HIT, 1.0), 5200) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = T_HATCH; t0 = a
    while t0 < HIT - 0.3:
        p = np.clip((t0 - a) / (HIT - a), 0, 1); g = 0.4 + 0.6 * p
        add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g); t0 += 0.95 - 0.35 * p
    return x * 0.5
def rip(d=0.55):
    """ガムテープを引き出して切る音"""
    t = tt(d); x = highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 6000), 900) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 70 * t))) * np.sin(np.pi * t / d) ** 0.5
    return x.astype(np.float32)
def slide(d=0.8):
    """引き戸がレールの上をすべる音"""
    t = tt(d); x = lowpass(rng.standard_normal(len(t)).astype(np.float32), 600) * (0.7 + 0.3 * np.sin(2 * np.pi * 23 * t)) * np.sin(np.pi * t / d) ** 0.6
    tk = tt(0.12); add(x, d - 0.08, (np.sin(2 * np.pi * 180 * tk) * np.exp(-tk * 40)).astype(np.float32), 0.8)
    return x.astype(np.float32)
def click():
    t = tt(0.05); return (np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 200) + highpass(rng.standard_normal(len(t)).astype(np.float32), 3000) * np.exp(-t * 300) * 0.5).astype(np.float32)
def creak(d=0.9, f0=140):
    """天井の板が重みできしむ音"""
    t = tt(d); f = f0 * (1 + 0.35 * (t / d) ** 1.5) * (1 + 0.03 * np.sin(2 * np.pi * 7 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.7 * np.sin(2.03 * ph) + 0.45 * np.sin(3.1 * ph) + 0.25 * np.sin(4.4 * ph)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 29 * t)))
    return lowpass((x * np.sin(np.pi * t / d) ** 1.1).astype(np.float32), 2200)
def dust():
    x = np.zeros(int(1.6 * SR), np.float32)
    for _ in range(26):
        tk = tt(0.03); add(x, rng.uniform(0, 1.4), (highpass(rng.standard_normal(len(tk)).astype(np.float32), 2500) * np.exp(-tk * 160)).astype(np.float32), rng.uniform(0.2, 0.8))
    return x
def scrape(d=1.3):
    """点検口のふたが、板の上をずれていく音"""
    t = tt(d); x = highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 2500), 300) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 17 * t + 3 * np.sin(2 * np.pi * 2 * t)))) * np.sin(np.pi * t / d) ** 0.7
    return x.astype(np.float32)
def whoosh(d=1.2):
    t = tt(d); return lowpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.sin(np.pi * t / d) ** 2
def taiko(g=1.0):
    t = tt(3.0); f = 46 + 60 * np.exp(-t * 14)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 500) * np.exp(-t * 12) * 2.5
    return (x * g).astype(np.float32)
def stinger():
    t = tt(2.4); x = np.zeros(len(t), np.float32)
    for k, n in enumerate([60, 61, 66, 67, 72, 73.5, 78, 85]):
        f = midi(n) * (1 - 0.06 * t / 2.4) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.3 * np.sign(np.sin(ph))).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.7) + highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + taiko(0.9)[:len(t)]
def resample(x, k):
    n = int(len(x) / k); return np.interp(np.arange(n) * k, np.arange(len(x)), x).astype(np.float32)

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    room = [reverb_ir(0.5, 1, 3500), reverb_ir(0.5, 2, 3500)]; attic = [reverb_ir(1.1, 3, 1800), reverb_ir(1.1, 4, 1800)]; hall = [reverb_ir(3.6, 5), reverb_ir(3.6, 6)]
    big = np.zeros(N, np.float32); fx = np.zeros(N, np.float32); up = np.zeros(N, np.float32)
    add(big, 0.0, taiko(0.45)); add(fx, T_FACE, whoosh(1.4), 0.12); add(big, T_FACE + 0.3, taiko(0.5))
    add(fx, L['l2']['start'] + 0.7, rip(0.6), 0.25); add(fx, L['l2']['start'] + 1.5, rip(0.4), 0.22)
    add(big, T_POINT, taiko(0.55))
    for k, tm in enumerate(MOUTH): add(big, tm, taiko(0.35 + 0.15 * k))
    add(fx, T_OPEN, slide(0.8), 0.35); add(fx, T_LIGHT, click(), 0.4); add(big, T_HATCH + 0.5, taiko(0.7))
    add(up, T_CREAK, creak(0.9, 130), 0.3); add(up, T_CREAK + 0.15, dust(), 0.25); add(up, T_CREAK + 1.2, creak(0.6, 150), 0.25)
    add(up, T_SLIDE, scrape(1.4), 0.3); add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']:
        if l['id'] == 'now': add(last, l['start'], resample(segs['now'], 0.86))       # 低くして、男の声に
        else: add(nar, l['start'], segs[l['id']])
    last = lowpass(last, 3200) * 1.1
    hop = SR // 20; rms = np.sqrt(np.mean(nar[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    ky = keys(); bedm = drone() * ramp(0, 0.6, 0.35, 1) + strings(); rt = roomtone() * 0.05
    hush = 1 - 0.8 * ramp(T_CREAK - 0.3, T_CREAK)                 # ギシッ、のあとは、部屋の音も静まる
    hb = heartbeat(); out = []
    for ch in range(2):
        music = (bedm + ky * 0.55 + conv(ky, hall[ch]) * 0.5) * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        sfx = big + conv(big, hall[ch]) * 0.25 + hb + rt * hush + fx + conv(fx, room[ch]) * 0.5 + up + conv(up, attic[ch]) * 0.8
        voice = nar + conv(nar, room[ch]) * 0.03 + last + conv(last, attic[ch]) * 0.5
        out.append(music * duck + sfx + voice)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([(bedm + ky * 0.55 + conv(ky, hall[c]) * 0.5) * 2.5 for c in range(2)], axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
