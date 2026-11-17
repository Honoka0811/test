# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(131)

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

T_ALARM = 0.45                                   # 警報が鳴りだす
T_DOWN = L['l3']['start'] - 0.2                  # 遮断機が下りる
T_STOPA = L['l11']['start'] + 1.25               # 警報が止まる
T_UP = T_STOPA + 0.9                             # 遮断機が上がる
FLICK = [T_UP + 1.5, T_UP + 2.35, T_UP + 3.1, T_UP + 3.75]   # 街灯がつくたびに、近づいている
HIT = L['now']['end'] + 0.5
PERIOD = 0.46                                    # 警報の間隔(左右のランプが交互に光る)
EV = dict(alarm=T_ALARM, down=T_DOWN, stop=T_STOPA, up=T_UP, flick=FLICK, period=PERIOD, t_far=L['l4']['start'] + 1.6, t_wide=L['l6']['start'] - 0.3,
          t_far2=L['l8']['start'] + 1.2, shake=L['l10']['start'], hit=HIT)

def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(25), 1.0), (midi(25) * 1.006, 0.8), (midi(37), 0.4), (midi(44), 0.16), (midi(38), 0.07)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)).astype(np.float32)
    return (x * 0.11 + lowpass(rng.standard_normal(N).astype(np.float32), 90) * 0.5).astype(np.float32)
def kan(f=700.0):
    """踏切の「カン」。2つの近い音が重なって、うなる"""
    t = tt(0.5); x = (np.sin(2 * np.pi * f * t) + 0.8 * np.sin(2 * np.pi * f * 1.07 * t) + 0.35 * np.sin(2 * np.pi * f * 2.02 * t) + 0.2 * np.sin(2 * np.pi * f * 2.9 * t)) * np.exp(-t * 7.5)
    x[:72] *= np.linspace(0, 1, 72); return x.astype(np.float32)
def alarm():
    x = np.zeros(N, np.float32); t0 = T_ALARM; k = 0
    while t0 < T_STOPA:
        add(x, t0, kan(), 1.0); t0 += PERIOD; k += 1
    return x
def motor(d):
    """遮断機が動くモーター音"""
    t = tt(d); x = np.sin(2 * np.pi * 118 * t + 2 * np.sin(2 * np.pi * 31 * t)) + 0.5 * np.sign(np.sin(2 * np.pi * 236 * t))
    return lowpass((x * np.sin(np.pi * t / d) ** 0.4).astype(np.float32), 1400)
def clack():
    t = tt(0.25); return (np.sin(2 * np.pi * 240 * t) * np.exp(-t * 40) + highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 5000), 900) * np.exp(-t * 60) * 1.5).astype(np.float32)
def rattle(d=3.0):
    """遮断棒が揺さぶられる、金属のがたつき"""
    x = np.zeros(int(d * SR), np.float32); t0 = 0.0
    while t0 < d - 0.3:
        t = tt(0.12); f = rng.uniform(900, 1700); add(x, t0, (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 2.4 * t)) * np.exp(-t * 55) + highpass(rng.standard_normal(len(t)).astype(np.float32), 2500) * np.exp(-t * 90) * 0.6, rng.uniform(0.4, 1.0)); t0 += rng.uniform(0.07, 0.22)
    return x
def heel():
    t = tt(0.2); return (np.sin(2 * np.pi * 1150 * t) * np.exp(-t * 70) + 0.6 * np.sin(2 * np.pi * 320 * t) * np.exp(-t * 40) + highpass(rng.standard_normal(len(t)).astype(np.float32), 1500) * np.exp(-t * 110) * 0.7).astype(np.float32)
def zap():
    """切れかけの街灯がつく音"""
    t = tt(0.3); x = np.sign(np.sin(2 * np.pi * 100 * t)) * (rng.random(len(t)) > 0.35) * np.exp(-t * 9); return highpass(x.astype(np.float32), 600)
def wind():
    x = lowpass(rng.standard_normal(N).astype(np.float32), 420); t = np.arange(N) / SR
    return x * (0.55 + 0.45 * np.sin(2 * np.pi * 0.11 * t + 1)) * 0.45
def strings():
    t = np.arange(N) / SR
    def cluster(a, b, peak):
        prog = np.clip((t - a) / (b - a), 0, 1); y = np.zeros(N, np.float32)
        for k, n in enumerate([73, 74, 79, 80, 85, 86.5, 91]):
            f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
            y += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
        return y * (ramp(a, b) ** 2 * peak) * (1 - ramp(b - 0.05, b + 0.15))
    return lowpass(cluster(L['l4']['start'], L['l6']['start'], 0.3) + cluster(L['l8']['start'], T_STOPA, 0.8) + cluster(T_UP, HIT, 1.0), 5200) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = T_STOPA + 0.3; t0 = a
    while t0 < HIT - 0.3:
        p = np.clip((t0 - a) / (HIT - a), 0, 1); g = 0.45 + 0.55 * p
        add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g); t0 += 0.9 - 0.4 * p
    return x * 0.55
def taiko(g=1.0):
    t = tt(3.0); f = 46 + 60 * np.exp(-t * 14)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 500) * np.exp(-t * 12) * 2.5
    return (x * g).astype(np.float32)
def stinger():
    t = tt(2.4); x = np.zeros(len(t), np.float32)
    for k, n in enumerate([61, 62, 67, 68, 73, 74.5, 79, 86]):
        f = midi(n) * (1 - 0.06 * t / 2.4) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.3 * np.sign(np.sin(ph))).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.7) + highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + taiko(0.9)[:len(t)]

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    hall = [reverb_ir(3.8, 1), reverb_ir(3.8, 2)]; street = [reverb_ir(1.4, 3, 3500), reverb_ir(1.4, 4, 3500)]
    big = np.zeros(N, np.float32); mech = np.zeros(N, np.float32); farfx = np.zeros(N, np.float32); lamp = np.zeros(N, np.float32)
    add(big, 0.0, taiko(0.5)); add(big, L['l4']['start'] + 2.2, taiko(0.6)); add(big, L['l9']['start'] + 1.2, taiko(0.6)); add(big, T_STOPA, taiko(0.85))
    add(mech, T_DOWN, motor(1.7), 0.07); add(mech, T_DOWN + 1.7, clack(), 0.3)
    add(mech, T_UP, motor(2.2), 0.08); add(mech, T_UP + 2.2, clack(), 0.25)
    add(farfx, EV['shake'] + 0.2, rattle(L['l10']['end'] - L['l10']['start'] + 1.6), 0.10)     # 向こうの遮断棒が揺さぶられる
    for i, tf in enumerate(FLICK):
        add(lamp, tf, zap(), 0.10)
        if i: add(farfx, tf - 0.42, heel(), 0.25 + 0.2 * i); add(farfx, tf - 0.12, heel(), 0.3 + 0.2 * i)   # 暗い間に、足音だけが近づく
    add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']: add(last if l['id'] == 'now' else nar, l['start'], segs[l['id']])
    hop = SR // 20; rms = np.sqrt(np.mean(nar[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.55 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    al = alarm() * 0.085
    bedm = drone() * ramp(0, 0.6, 0.35, 1) * (1 - 0.7 * ramp(T_STOPA, T_STOPA + 0.1) * (1 - ramp(T_UP + 1.0, T_UP + 3.0))) + strings() + wind() * 0.5
    hb = heartbeat(); out = []
    for ch in range(2):
        music = bedm * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        alm = (al + conv(al, street[ch]) * 0.35) * (1.0 if ch == 0 else 0.7)                       # 警報機は左手前
        sfx = big + conv(big, hall[ch]) * 0.25 + hb + (mech + conv(mech, street[ch]) * 0.5) * (0.7 if ch == 0 else 1.0) + farfx * 0.6 + conv(farfx, street[ch]) * 0.9 + lamp * (0.6 if ch == 0 else 1.0)
        out.append((music + alm) * duck + sfx + nar + conv(nar, street[ch]) * 0.03 + last * (1.0 if ch == 0 else 0.75) + conv(last, hall[ch]) * 0.6)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([bedm * 2.5] * 2, axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
