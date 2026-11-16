# -*- coding: utf-8 -*-
"""BGM・効果音・「アプリに録音されていた音」を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
録音再生パートの音量包絡を events.json に書き出し、映像の波形表示に使う。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(41)

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
def window(a, b, f=0.12):
    return ramp(a, a + f) * (1 - ramp(b - f, b))

# 再生区間 [開始, 終了]
P1 = (L['r1']['end'] + 0.3, L['r1']['end'] + 3.7)
RP = (L['again']['end'] + 0.3, L['again']['end'] + 4.3)   # 1件目をもう一度(いびきを抑えて)
P2 = (L['r2']['end'] + 0.25, L['c2']['end'] + 0.65)
P3 = (L['r3']['end'] + 0.25, L['c3']['end'] + 0.75)
LIVE = (L['enter']['end'] + 0.5, L['now']['end'] + 0.5)
HIT = LIVE[1]
RP_CREAK = (RP[0] + 0.45, RP[0] + 1.55); RP_STEPS = [RP[0] + 1.85 + 0.48 * k for k in range(4)]
EV = dict(replay=RP, rp_click=RP[0] + 0.15, rp_creak=RP_CREAK, rp_steps=RP_STEPS, t_replay=L['again']['start'] - 0.25, p1=P1, p2=P2, p3=P3, live=LIVE, hit=HIT, detail=L['stop']['start'] - 0.3, list=L['open']['start'] - 0.25)

# ---------------- BGM ----------------
def pad():
    """ゆっくりうねる暗いパッド"""
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(26), 1.0), (midi(26) * 1.006, 0.8), (midi(38), 0.45), (midi(41), 0.22), (midi(45), 0.16), (midi(44), 0.07)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.08 * t)).astype(np.float32)
    return (x * 0.11 + lowpass(rng.standard_normal(N).astype(np.float32), 90) * 0.5).astype(np.float32)
def celesta(f, dur=4.0):
    t = tt(dur); x = np.sin(2 * np.pi * f * t) * np.exp(-t * 1.4) + 0.4 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 5) + 0.15 * np.sin(2 * np.pi * 6.3 * f * t) * np.exp(-t * 9)
    x[:96] *= np.linspace(0, 1, 96); return x.astype(np.float32)
def lullaby():
    """壊れかけの子守唄(Dマイナー、ところどころ半音ずれる)"""
    x = np.zeros(N, np.float32); seq = [69, 74, 77, 76, 74, 69, 70, 68, 69, 74, 77, 81, 80, 77, 75, 74]
    t0 = 1.2; i = 0
    while t0 < HIT - 3:
        add(x, t0, celesta(midi(seq[i % 16]) * (1 + rng.uniform(-0.004, 0.004))), 0.17)
        if i % 4 == 0: add(x, t0, celesta(midi(seq[i % 16] - 24), 5), 0.14)
        t0 += 1.45 if i % 2 == 0 else 1.05; i += 1
    return x
def clock():
    x = np.zeros(N, np.float32); t = tt(0.03); k = 0
    while k < DUR:
        add(x, k, np.sin(2 * np.pi * (2400 if int(k) % 2 else 2000) * t) * np.exp(-t * 220), 0.05); k += 1.0
    return x
def strings():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32); a, b = L['stop']['start'], HIT
    prog = np.clip((t - a) / (b - a), 0, 1)
    for k, n in enumerate([74, 75, 80, 81, 86, 87.5, 92]):
        f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k))
        ph = 2 * np.pi * np.cumsum(f) / SR
        x += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
    env = ramp(L['r3']['start'], a, 0, 0.10) + ramp(a, b, 0, 0.9) ** 2 * 0.9
    return lowpass(x, 5200) * env * (1 - ramp(b - 0.05, b + 0.1)) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = L['stop']['start']; t0 = a
    while t0 < HIT - 0.3:
        p = np.clip((t0 - a) / (HIT - a), 0, 1); g = 0.3 + 0.7 * p
        add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g); t0 += 1.05 - 0.45 * p
    return x * 0.5

# ---------------- 録音されていた音 ----------------
def snore(d=1.5):
    t = tt(d); w = rng.standard_normal(len(t)).astype(np.float32); n = lowpass(w, 420) + lowpass(w, 1600) * 0.55
    flut = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 27 * t + 3 * np.sin(2 * np.pi * 1.3 * t)))
    return (n * flut * np.sin(np.pi * t / d) ** 1.5 * 9).astype(np.float32)
def breath_out(d=1.0):
    t = tt(d); return highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 2500), 700) * np.sin(np.pi * t / d) ** 2 * 0.6
def creak(d=0.9, f0=310):
    """ドアや床がきしむ音"""
    t = tt(d); f = f0 * (1 + 0.5 * (t / d) ** 2) * (1 + 0.03 * np.sin(2 * np.pi * 9 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.6 * np.sin(2.02 * ph) + 0.4 * np.sin(3.1 * ph)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * t)))
    return (x * np.sin(np.pi * t / d) ** 1.2).astype(np.float32)
def step():
    t = tt(0.35); return (np.sin(2 * np.pi * 95 * t) * np.exp(-t * 22) + 0.7 * np.sin(2 * np.pi * 260 * t) * np.exp(-t * 40) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 1500) * np.exp(-t * 45) * 2.5).astype(np.float32)
def latch():
    """ドアノブが回る「カチャ」"""
    x = np.zeros(int(0.25 * SR), np.float32)
    for dt, f, g in [(0, 2100, 1.0), (0.07, 1500, 0.8)]:
        t = tt(0.08); add(x, dt, (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.7 * t)) * np.exp(-t * 70) * g + highpass(rng.standard_normal(len(t)).astype(np.float32), 2000) * np.exp(-t * 120) * 0.6)
    return x
def rustle(d=0.7):
    t = tt(d); return highpass(rng.standard_normal(len(t)).astype(np.float32), 1800) * np.sin(np.pi * t / d) ** 2 * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t))
def tick():
    t = tt(0.05); return (np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 120)).astype(np.float32)
def ping():
    x = np.zeros(int(0.7 * SR), np.float32)
    for dt, f in [(0, 1046.5), (0.13, 1568)]:
        t = tt(0.5); add(x, dt, (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 11))
    return x
def boom(g=1.0):
    t = tt(3.0); f = 34 + 50 * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 300) * np.exp(-t * 7) * 2.5
    return (x * g).astype(np.float32)
def stinger():
    t = tt(2.4); x = np.zeros(len(t), np.float32)
    for k, n in enumerate([62, 63, 68, 69, 74, 75.5, 80, 87]):
        f = midi(n) * (1 - 0.06 * t / 2.4) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.3 * np.sign(np.sin(ph))).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.7) + highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + boom(0.9)[:len(t)]

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    hall = [reverb_ir(3.6, 1), reverb_ir(3.6, 2)]; room = [reverb_ir(0.9, 3, 3000), reverb_ir(0.9, 4, 3000)]
    # --- 録音トラック(スマホのマイクで録った質感にする) ---
    rec = np.zeros(N, np.float32)
    a = P1[0]
    add(rec, a + 0.05, snore(1.3), 0.26); add(rec, a + 1.3, breath_out(0.5), 0.3)
    add(rec, a + 1.35, latch(), 0.25); add(rec, a + 1.5, creak(0.9, 420), 0.22)   # いびきの合間に、ドアが開く(伏線)
    add(rec, a + 2.5, step(), 0.5); add(rec, a + 2.95, step(), 0.65)             # 近づく足音
    # もう一度再生: いびきを抑え、ドアと足音をはっきり聞かせる
    a = RP[0]
    add(rec, a + 0.05, snore(1.3), 0.05); add(rec, a + 2.3, snore(1.2), 0.04)
    add(rec, EV['rp_click'], latch(), 0.6); add(rec, RP_CREAK[0], creak(1.1, 420), 0.5)
    for k, ts in enumerate(RP_STEPS): add(rec, ts, step(), 0.55 + 0.25 * k)
    a = P2[0]
    add(rec, a + 0.05, rustle(0.7), 0.35); add(rec, L['c2']['start'], segs['c2'], 1.8); add(rec, L['c2']['end'] + 0.1, step(), 0.2)
    a = P3[0]
    add(rec, a + 0.1, creak(0.8, 380), 0.22); add(rec, L['c3']['start'], segs['c3'], 1.25); add(rec, L['c3']['end'] + 0.15, breath_out(0.5), 0.5)
    hiss = highpass(lowpass(rng.standard_normal(N).astype(np.float32), 5000), 300) * 0.02
    win = window(*P1) + window(*P2) + window(*P3) + window(*RP)
    rec = lowpass(highpass(rec + hiss * win, 180), 3800) * win
    live = np.zeros(N, np.float32)
    add(live, L['now']['start'], segs['now'], 1.25); add(live, LIVE[0] + 0.5, breath_out(0.8), 0.4)
    live += hiss * 1.5 * window(LIVE[0], HIT + 0.05, 0.3)
    # 波形表示用の包絡
    def envelope(x):
        hop = SR // FPS; n = N // hop; e = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1))
        return [round(float(v), 4) for v in np.clip(e / 0.12, 0, 1) ** 0.6]
    EV['env'] = envelope(rec + live)
    # --- BGM ---
    inplay = np.clip(win + window(LIVE[0], HIT, 0.3), 0, 1)
    lb = lullaby()
    bed = (pad() * ramp(0, 0.6, 0.35, 1) + strings() + clock()) * (1 - 0.7 * inplay) * (1 - ramp(HIT, HIT + 0.1) * 0.75)
    ui = np.zeros(N, np.float32); big = np.zeros(N, np.float32)
    for p in (P1, P2, P3, RP): add(ui, p[0] - 0.12, tick(), 0.25); add(ui, p[1], tick(), 0.15)
    for k in range(3): add(ui, EV['list'] + 0.35 + 0.3 * k, tick(), 0.14)
    add(ui, LIVE[0] - 0.25, ping(), 0.22)
    add(big, 0.0, boom(0.7)); add(big, L['stop']['start'] + 2.3, boom(0.5))
    add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32)
    for l in TL['lines']:
        if l['kind'] == 'nar': add(nar, l['start'], segs[l['id']])
    hop = SR // 20; rms = np.sqrt(np.mean(nar[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    hb = heartbeat(); out = []
    for ch in range(2):
        music = (bed + (lb * 0.5 + conv(lb, hall[ch]) * 0.5) * (1 - 0.8 * inplay)) * duck
        fx = big + conv(big, hall[ch]) * 0.2 + hb + ui + rec * 1.5 + live * (1.0 if ch == 0 else 0.75) + conv(live, hall[ch]) * 0.5
        out.append(music + fx + nar + conv(nar, room[ch]) * 0.04)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y)
    save('bgm.wav', np.stack([(pad() + lb * 0.5 + conv(lb, hall[c]) * 0.5) * 2.5 for c in range(2)], axis=1))
    np.save(os.path.join(HERE, 'output', 'rec.npy'), rec)
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
