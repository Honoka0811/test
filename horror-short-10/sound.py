# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(149)

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

T_GLOW = L['l3']['start'] - 0.6                  # バスのライトが近づく
T_RISE = L['l3']['start'] + 1.0                  # 立ち上がろうとする
T_GRAB = L['l3']['start'] + 3.0                  # 袖をつかまれる
T_BUS = L['l5']['start'] - 0.5                   # バスが目の前を通りすぎる
BUS_D = 2.7
T_SIGN = L['l6']['start'] + 0.3                  # 時刻表に寄る
T_STICK = L['l6']['start'] + 2.6                 # 「廃止」
T_WIDE = L['l7']['start'] - 0.3
T_FLASH0 = 1.45                                  # 冒頭の遠い雷(一瞬だけ人影が映る)
T_FLASH = L['l7']['start'] + 1.35                # 雷が光って、まわりの人影が見える
T_TURN = L['g4']['start'] - 0.6                  # 女の子がこちらを向く
HIT = L['g4']['end'] + 0.5                       # 街灯が消え、もう一度雷が光る
EV = dict(t_close=L['g1']['start'] - 0.5, glow=T_GLOW, rise=T_RISE, grab=T_GRAB, bus=T_BUS, bus_d=BUS_D, t_sign=T_SIGN, stick=T_STICK, t_wide=T_WIDE,
          flash0=T_FLASH0, flash=T_FLASH, turn=T_TURN, hit=HIT)

def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(26), 1.0), (midi(26) * 1.006, 0.8), (midi(38), 0.4), (midi(45), 0.16), (midi(41), 0.1)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)).astype(np.float32)
    return (x * 0.09 + lowpass(rng.standard_normal(N).astype(np.float32), 90) * 0.4).astype(np.float32)
def box(f, dur=3.5):
    t = tt(dur); x = np.sin(2 * np.pi * f * t) * np.exp(-t * 1.7) + 0.45 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 4) + 0.2 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t * 8)
    x[:96] *= np.linspace(0, 1, 96); return x.astype(np.float32)
def lullaby():
    """オルゴールの子守唄(自作・Dマイナー、3拍子)。約束のあとから少しずつ遅く、低くなる"""
    x = np.zeros(N, np.float32); mel = [(0, 69), (1, 72), (2, 74), (3, 77), (5, 76), (6, 74), (8, 72), (9, 69), (11, 70), (12, 69), (14, 65), (15, 62),
                                        (18, 69), (19, 72), (20, 74), (21, 81), (23, 79), (24, 77), (26, 76), (27, 74), (29, 73), (30, 74)]
    t0 = 1.0; beat = 0.5
    while t0 < HIT - 3:
        for b, n in mel:
            tn = t0 + b * beat
            if tn > T_STICK - 0.3: continue
            late = max(0.0, (tn - L['g2']['end']) / (T_STICK - L['g2']['end']))
            add(x, tn + 0.25 * late * b * 0.1, box(midi(n) * (1 - 0.03 * late ** 2) * (1 + rng.uniform(-0.003, 0.003))), 0.15)
            if b % 6 == 0: add(x, tn, box(midi(n - 24), 5), 0.14)
        t0 += 36 * beat
    return x
def rain():
    """雨: 細かい雨粒の音の層と、屋根を打つ音、しずく"""
    x = highpass(lowpass(rng.standard_normal(N).astype(np.float32), 9000), 1800) * 0.5 + highpass(lowpass(rng.standard_normal(N).astype(np.float32), 2200), 500) * 0.35
    t = np.arange(N) / SR; x *= (0.85 + 0.15 * np.sin(2 * np.pi * 0.17 * t)).astype(np.float32)
    for _ in range(int(DUR * 16)):                                    # 屋根を打つ大きめの粒
        tk = tt(0.05); add(x, rng.uniform(0, DUR - 0.1), (np.sin(2 * np.pi * rng.uniform(700, 1800) * tk) * np.exp(-tk * 130)).astype(np.float32), rng.uniform(0.5, 1.6))
    for k in np.arange(0.4, DUR - 0.3, 0.83):                         # 屋根のふちから落ちるしずく
        tk = tt(0.09); f = 1250 * (1 + 0.7 * tk / 0.09); add(x, k + rng.uniform(-0.05, 0.05), (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tk * 55)).astype(np.float32), 1.6)
    return x * 0.035
def bus():
    """濡れた道を走るバス: エンジンの低音、タイヤが水を切る音、水しぶき"""
    d = BUS_D + 1.6; t = tt(d); env = np.clip(t / 0.7, 0, 1) ** 2 * np.clip((d - t) / 1.6, 0, 1)
    eng = np.sin(2 * np.pi * 62 * t + 1.5 * np.sin(2 * np.pi * 31 * t)) + 0.5 * np.sign(np.sin(2 * np.pi * 124 * t))
    x = lowpass(eng.astype(np.float32), 700) * 0.9 + lowpass(rng.standard_normal(len(t)).astype(np.float32), 500) * 1.0 + highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 7000), 1500) * 0.7
    x = x * env
    ts = tt(0.9); sp = highpass(rng.standard_normal(len(ts)).astype(np.float32), 900) * np.sin(np.pi * ts / 0.9) ** 0.5 * np.exp(-ts * 2.5)
    add(x, 0.9, sp, 1.6)
    return x.astype(np.float32)
def approach():
    t = tt(4.5); x = lowpass((np.sin(2 * np.pi * 62 * t + 1.5 * np.sin(2 * np.pi * 31 * t))).astype(np.float32), 500) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 300)
    return x * (t / 4.5) ** 2.5
def thunder():
    t = tt(4.0); x = lowpass(rng.standard_normal(len(t)).astype(np.float32), 160) * np.exp(-t * 1.1) * (1 + 0.6 * np.sin(2 * np.pi * 3.1 * t)); x[:2400] *= np.linspace(0, 1, 2400); return x * 4
def crack():
    """近くに落ちる雷: 鋭い破裂音のあと、長いとどろき"""
    t = tt(5.0); x = lowpass(rng.standard_normal(len(t)).astype(np.float32), 170) * np.exp(-t * 0.9) * (1 + 0.6 * np.sin(2 * np.pi * 2.7 * t)) * 5
    tc = tt(0.5); add(x, 0.0, highpass(lowpass(rng.standard_normal(len(tc)).astype(np.float32), 6000), 300) * np.exp(-tc * 9) * 2.2)
    add(x, 0.33, highpass(lowpass(rng.standard_normal(len(tc)).astype(np.float32), 4000), 200) * np.exp(-tc * 12) * 1.3)
    return x.astype(np.float32)
def strings():
    t = np.arange(N) / SR
    def cluster(a, b, peak):
        prog = np.clip((t - a) / (b - a), 0, 1); y = np.zeros(N, np.float32)
        for k, n in enumerate([74, 75, 80, 81, 86, 87.5, 92]):
            f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
            y += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
        return y * (ramp(a, b) ** 2 * peak) * (1 - ramp(b - 0.05, b + 0.15))
    return lowpass(cluster(L['g2']['end'], T_BUS, 0.5) + cluster(T_SIGN, T_FLASH, 0.7) + cluster(T_FLASH + 0.5, HIT, 1.0), 5200) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = T_GRAB; t0 = a
    while t0 < HIT - 0.3:
        p = np.clip((t0 - a) / (HIT - a), 0, 1); g = 0.4 + 0.6 * p
        add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g); t0 += 0.95 - 0.35 * p
    return x * 0.5
def taiko(g=1.0):
    t = tt(3.0); f = 46 + 60 * np.exp(-t * 14)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 500) * np.exp(-t * 12) * 2.5
    return (x * g).astype(np.float32)
def stinger():
    t = tt(2.4); x = np.zeros(len(t), np.float32)
    for k, n in enumerate([62, 63, 68, 69, 74, 75.5, 80, 87]):
        f = midi(n) * (1 - 0.06 * t / 2.4) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.3 * np.sign(np.sin(ph))).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.7) + highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + taiko(0.9)[:len(t)]
def zap():
    t = tt(0.3); x = np.sign(np.sin(2 * np.pi * 100 * t)) * (rng.random(len(t)) > 0.35) * np.exp(-t * 9); return highpass(x.astype(np.float32), 600)

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    hall = [reverb_ir(3.8, 1), reverb_ir(3.8, 2)]; street = [reverb_ir(1.2, 3, 3500), reverb_ir(1.2, 4, 3500)]
    big = np.zeros(N, np.float32); veh = np.zeros(N, np.float32); fx = np.zeros(N, np.float32)
    add(big, 0.0, taiko(0.5)); add(big, T_FLASH0 + 0.9, thunder(), 0.10); add(big, T_GRAB, taiko(0.8)); add(big, T_STICK, taiko(0.85)); add(big, T_FLASH + 0.12, crack(), 0.5); add(big, HIT + 0.1, crack(), 0.45)
    add(veh, T_BUS - 4.3, approach(), 0.10); add(veh, T_BUS - 0.5, bus(), 0.2)
    add(fx, HIT - 0.05, zap(), 0.16); add(big, HIT, stinger(), 0.7)
    nar = np.zeros(N, np.float32); girl = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']: add(last if l['id'] == 'g4' else girl if l['id'] in ('g1', 'g2', 'g3') else nar, l['start'], segs[l['id']])
    allv = nar + girl
    hop = SR // 20; rms = np.sqrt(np.mean(allv[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    rn = rain(); lb = lullaby(); bedm = drone() * ramp(0, 0.6, 0.35, 1) + strings()
    hush = 1 - 0.6 * ramp(T_STICK, T_STICK + 0.3) * (1 - ramp(T_FLASH, T_FLASH + 0.3) * 0.6)                          # 「廃止」のあと、雨音が遠のく
    hb = heartbeat(); out = []
    for ch in range(2):
        r2 = rn if ch == 0 else np.roll(rn, 7919)
        music = (bedm + lb * 0.5 + conv(lb, hall[ch]) * 0.55) * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        sfx = big + conv(big, hall[ch]) * 0.25 + hb + r2 * hush * (1 - ramp(HIT, HIT + 0.2) * 0.5) + veh * (0.8 if ch == 0 else 1.0) + conv(veh, street[ch]) * 0.3 + fx
        voice = nar + conv(nar, street[ch]) * 0.03 + (girl * 0.95 + conv(girl, street[ch]) * 0.25) * (1.0 if ch == 0 else 0.7) + last * (1.0 if ch == 0 else 0.7) + conv(last, hall[ch]) * 0.6
        out.append(music * duck + sfx + voice)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([(bedm + lb * 0.5 + conv(lb, hall[c]) * 0.55) * 2.5 for c in range(2)], axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
