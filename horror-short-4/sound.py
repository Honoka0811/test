# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
距離の推移(キーフレーム)と電話音声の音量包絡を events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(53)

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

# 距離[m]のキーフレーム(時刻, 距離)。映像もこれを使う
DK = [(0, 1150), (L['l1']['start'], 900), (L['l2']['end'], 640), (L['l3']['end'], 330), (L['l4']['start'] + 1.0, 290),
      (L['l4']['end'], 95), (L['l5']['start'] + 1.2, 11), (L['l7']['start'] + 0.4, 11), (L['l8']['start'] + 0.1, 0)]
def dist(t): return float(np.interp(t, [k[0] for k in DK], [k[1] for k in DK]))
T_ZERO = DK[-1][0]
T_BUZZ = L['l8']['end'] + 0.3
CALL = (L['call']['start'] - 0.35, L['call2']['end'] + 0.3)
RING = (L['call2']['end'] + 0.75, L['now']['start'] - 0.25)   # ミキが鳴らした「スマホを探す」音
HIT = L['now']['end'] + 0.5
EV = dict(dk=DK, zero=T_ZERO, buzz=T_BUZZ, call=CALL, ring=L['l9']['start'] - 0.2, hit=HIT, ringsnd=RING, bed=L['l12']['start'] + 0.8)

def pad():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(24), 1.0), (midi(24) * 1.006, 0.8), (midi(36), 0.45), (midi(43), 0.18), (midi(39), 0.14), (midi(37), 0.06)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.08 * t)).astype(np.float32)
    return (x * 0.11 + lowpass(rng.standard_normal(N).astype(np.float32), 90) * 0.5).astype(np.float32)
def pulse_bass():
    """近づくほど速くなる低いパルス"""
    x = np.zeros(N, np.float32); t0 = L['l1']['start']
    while t0 < T_ZERO:
        d = dist(t0); t = tt(0.35); f = midi(36) * (1 + 0.5 * np.exp(-t * 30))
        add(x, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9), 0.22 + 0.2 * (1 - min(d, 900) / 900))
        t0 += 0.3 + 0.75 * min(d, 900) / 900
    return x
def sonar(f=1320, d=0.5):
    t = tt(d); x = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 9); x[:96] *= np.linspace(0, 1, 96); return x.astype(np.float32)
def strings():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32); a, b = L['l9']['start'], HIT
    prog = np.clip((t - a) / (b - a), 0, 1)
    for k, n in enumerate([72, 73, 78, 79, 84, 85.5, 90]):
        f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
    env = ramp(L['l4']['start'], T_ZERO, 0, 0.22) * (1 - ramp(T_ZERO, T_ZERO + 0.2) * 0.6) + ramp(a, b, 0, 0.9) ** 2 * 0.9
    return lowpass(x, 5200) * env * (1 - ramp(b - 0.05, b + 0.1)) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = L['call2']['start']; t0 = a
    while t0 < HIT - 0.3:
        p = np.clip((t0 - a) / (HIT - a), 0, 1); g = 0.35 + 0.65 * p
        add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g); t0 += 0.95 - 0.4 * p
    return x * 0.5
def step():
    t = tt(0.35); return (np.sin(2 * np.pi * 95 * t) * np.exp(-t * 22) + 0.7 * np.sin(2 * np.pi * 260 * t) * np.exp(-t * 40) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 1500) * np.exp(-t * 45) * 2.5).astype(np.float32)
def creak(d=0.9, f0=380):
    t = tt(d); f = f0 * (1 + 0.5 * (t / d) ** 2) * (1 + 0.03 * np.sin(2 * np.pi * 9 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.6 * np.sin(2.02 * ph) + 0.4 * np.sin(3.1 * ph)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * t)))
    return (x * np.sin(np.pi * t / d) ** 1.2).astype(np.float32)
def buzz(d=0.7):
    t = tt(d); x = np.sign(np.sin(2 * np.pi * 165 * t)) * 0.5 + np.sin(2 * np.pi * 82 * t)
    return lowpass((x * np.sin(np.pi * t / d) ** 0.3).astype(np.float32), 900)
def tick():
    t = tt(0.05); return (np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 120)).astype(np.float32)
def boom(g=1.0):
    t = tt(3.0); f = 34 + 50 * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 300) * np.exp(-t * 7) * 2.5
    return (x * g).astype(np.float32)
def stinger():
    t = tt(2.4); x = np.zeros(len(t), np.float32)
    for k, n in enumerate([60, 61, 66, 67, 72, 73.5, 78, 85]):
        f = midi(n) * (1 - 0.06 * t / 2.4) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.3 * np.sign(np.sin(ph))).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.7) + highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + boom(0.9)[:len(t)]

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    hall = [reverb_ir(3.6, 1), reverb_ir(3.6, 2)]; room = [reverb_ir(0.9, 3, 3000), reverb_ir(0.9, 4, 3000)]
    ui = np.zeros(N, np.float32); big = np.zeros(N, np.float32); house = np.zeros(N, np.float32)
    # 接近を知らせる探知音: 近いほど間隔が短く、音が高くなる
    t0 = 0.5; pings = []
    while t0 < T_ZERO:
        d = dist(t0); add(ui, t0, sonar(1100 + 700 * (1 - min(d, 900) / 900)), 0.10 + 0.08 * (1 - min(d, 900) / 900)); pings.append(round(t0, 3))
        t0 += 0.22 + 1.25 * min(d, 900) / 900
    t = tt(1.1); add(ui, T_ZERO, np.sin(2 * np.pi * 1800 * t) * np.minimum(1, (1.1 - t) * 8), 0.14)     # 0m: 鳴りっぱなしの音
    EV['pings'] = pings
    # 「スマホを探す」音: ベッドの下からこもって聞こえる(右寄り)。ささやきの直前で急に止まる
    ringt = []; t0 = RING[0]
    while t0 < RING[1] - 0.3:
        for k in range(3): add(house, t0 + 0.14 * k, sonar(1568, 0.12), 0.5)
        ringt.append(round(t0, 3)); t0 += 0.85
    house[:] = lowpass(house, 2200)
    EV['rings'] = ringt
    for k in range(3): add(ui, T_BUZZ + 0.95 * k, buzz(0.65), 0.2)      # 着信のバイブ
    add(ui, CALL[0], tick(), 0.3); add(ui, CALL[1], tick(), 0.3)
    add(big, 0.0, boom(0.7)); add(big, T_ZERO, boom(0.8)); add(big, EV['bed'], boom(0.55)); add(big, HIT, stinger(), 0.75)
    # 声
    nar = np.zeros(N, np.float32); phone = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']:
        add(phone if l['id'] in ('call', 'call2') else last if l['id'] == 'now' else nar, l['start'], segs[l['id']])
    phone = lowpass(highpass(phone, 450), 3000) * 3.6        # 電話の音質
    phone += highpass(lowpass(rng.standard_normal(N).astype(np.float32), 3000), 500) * 0.012 * ramp(CALL[0], CALL[0] + 0.1) * (1 - ramp(CALL[1] - 0.1, CALL[1]))
    hop = SR // FPS; n = N // hop; e = np.sqrt(np.mean(phone[:n * hop].reshape(n, hop) ** 2, axis=1))
    EV['env'] = [round(float(v), 4) for v in np.clip(e / 0.12, 0, 1) ** 0.6]
    allv = nar + phone
    hop = SR // 20; rms = np.sqrt(np.mean(allv[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    quiet = 1 - 0.75 * ramp(L['l6']['start'] - 0.2, L['l6']['start'] + 0.3) * (1 - ramp(L['l7']['start'], L['l7']['start'] + 0.6))   # 「鳴りません」で静まる
    incall = 1 - 0.6 * ramp(CALL[0], CALL[0] + 0.2) * (1 - ramp(CALL[1], CALL[1] + 0.3))
    bed = (pad() * ramp(0, 0.6, 0.35, 1) + pulse_bass() + strings()) * quiet * incall * (1 - ramp(HIT, HIT + 0.1) * 0.75)
    hb = heartbeat(); out = []
    for ch in range(2):
        fx = big + conv(big, hall[ch]) * 0.2 + hb + (ui + conv(ui, hall[ch]) * 0.25) * quiet + (house + conv(house, room[ch]) * 0.8) * (0.6 if ch == 0 else 1.0)
        out.append(bed * duck + fx + nar + conv(nar, room[ch]) * 0.04 + phone + last * (1.0 if ch == 0 else 0.7) + conv(last, hall[ch]) * 0.6)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([bed * 2.5] * 2, axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
