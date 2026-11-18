# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(163)

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

T_IN = L['l2']['end'] + 0.3                     # トンネルに入る
T_BUMP = L['l3']['start'] - 0.75                 # 車が沈む(誰かが乗りこむ)
T_OUT = L['l5']['start'] + 0.2                   # トンネルを抜ける
T_FOG = T_OUT + 0.4                              # 窓が曇りはじめる
T_WIPE = L['l6']['start'] + 0.55                 # ワイパー(2往復)
PRINTS = [L['l8']['start'] + 2.0 + 0.55 * k for k in range(7)]   # 手形が1つずつ増える
T_VOICE = L['v']['start']
T_MIRROR = L['l10']['start'] - 0.2               # バックミラーに寄る
T_FULL = L['l10']['start'] + 1.65                # 後ろの席が、いっぱい
T_LEAN = L['now']['start'] - 0.4                 # まん中の影が、身を乗り出す
HIT = L['now']['end'] + 0.5
EV = dict(l2s=L['l2']['start'], l2e=L['l2']['end'], t_in=T_IN, bump=T_BUMP, t_out=T_OUT, fog=T_FOG, fogfull=L['l7']['end'], wipe=T_WIPE, prints=PRINTS,
          voice=T_VOICE, mirror=T_MIRROR, full=T_FULL, lean=T_LEAN, hit=HIT)

def engine():
    """エンジンとタイヤの音。車が沈んだあとは、重くなったぶん少し低くなる"""
    t = np.arange(N) / SR; load = 1 - 0.07 * ramp(T_BUMP, T_BUMP + 0.6)
    f = 34 * load * (1 + 0.03 * np.sin(2 * np.pi * 0.21 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.35 * np.sin(3 * ph) + 0.2 * np.sign(np.sin(4 * ph))).astype(np.float32)
    x = lowpass(x, 420) * 0.5 + lowpass(rng.standard_normal(N).astype(np.float32), 380) * 0.9 + highpass(lowpass(rng.standard_normal(N).astype(np.float32), 2500), 500) * 0.12
    return x
def drizzle():
    """トンネルを出たあとの、小雨がガラスに当たる音"""
    x = np.zeros(N, np.float32)
    for _ in range(int((DUR - T_OUT) * 7)):
        tk = tt(0.04); add(x, rng.uniform(T_OUT + 0.3, DUR - 0.1), (np.sin(2 * np.pi * rng.uniform(1400, 3000) * tk) * np.exp(-tk * 160)).astype(np.float32), rng.uniform(0.3, 1.0))
    return x
def whoosh(d=1.2):
    t = tt(d); return lowpass(rng.standard_normal(len(t)).astype(np.float32), 700) * np.sin(np.pi * t / d) ** 2
def thud():
    """車体が沈む「ドスン」と、サスペンションのきしみ"""
    t = tt(0.9); x = np.sin(2 * np.pi * (46 + 30 * np.exp(-t * 20)) * t) * np.exp(-t * 7) * 1.4 + lowpass(rng.standard_normal(len(t)).astype(np.float32), 400) * np.exp(-t * 16) * 1.5
    tc = tt(0.6); f = 190 * (1 - 0.3 * tc / 0.6); ph = 2 * np.pi * np.cumsum(f) / SR
    add(x, 0.12, ((np.sin(ph) + 0.5 * np.sin(2.03 * ph)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 31 * tc))) * np.sin(np.pi * tc / 0.6)).astype(np.float32), 0.25)
    return x.astype(np.float32)
def breath(d):
    """息づかい(吸って、吐く)"""
    t = tt(d); n = highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 2600), 350)
    env = np.where(t < d * 0.4, np.sin(np.pi * t / (d * 0.8)) * 0.6, np.clip(np.sin(np.pi * (t - d * 0.4) / (d * 1.2)), 0, 1) ** 1.5)
    return (n * env).astype(np.float32)
def breathing():
    """何人もの息。曇りが広がるにつれて、増えていく"""
    x = np.zeros(N, np.float32)
    for k, (per, ph, g) in enumerate([(3.3, 0.0, 1.0), (3.9, 1.3, 0.8), (2.9, 2.2, 0.7), (4.4, 0.7, 0.9), (3.6, 1.8, 0.6)]):
        t0 = T_FOG + 0.5 + k * 1.4 + ph
        while t0 < HIT - 0.5:
            add(x, t0, breath(per * 0.7), g); t0 += per
    return x * np.clip(ramp(T_FOG, L['l7']['end'] + 2) * 1.0, 0, 1) * (1 - 0.6 * ramp(T_LEAN, T_LEAN + 0.4))
def wiper():
    x = np.zeros(N, np.float32)
    for k in range(4):
        ts = T_WIPE + 0.62 * k; t = tt(0.55)
        mot = lowpass((np.sin(2 * np.pi * 95 * t) + 0.5 * np.sign(np.sin(2 * np.pi * 190 * t))).astype(np.float32), 900) * np.sin(np.pi * t / 0.55) * 0.35
        f = 1500 + 600 * np.sin(np.pi * t / 0.55); sq = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 47 * t))) * np.sin(np.pi * t / 0.55) * 0.12
        add(x, ts, (mot + sq).astype(np.float32)); tk = tt(0.08); add(x, ts + 0.55, (np.sin(2 * np.pi * 220 * tk) * np.exp(-tk * 60)).astype(np.float32), 0.4)
    return x
def squeak():
    """手のひらがガラスに押しつけられる音(ぺた、きゅっ)"""
    t = tt(0.5); x = lowpass(rng.standard_normal(len(t)).astype(np.float32), 1200) * np.exp(-t * 40) * 1.5
    tc = tt(0.3); f = 900 + 500 * (tc / 0.3); add(x, 0.07, (np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 63 * tc))) * np.sin(np.pi * tc / 0.3) * 0.35).astype(np.float32))
    return x.astype(np.float32)
def piano(f, dur=5.0):
    t = tt(dur); x = np.zeros(len(t), np.float32)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k); x += (np.sin(2 * np.pi * fk * t) * np.exp(-t * (0.7 + 0.45 * k)) / k ** 1.3).astype(np.float32)
    x[:144] *= np.linspace(0, 1, 144); return x
def keys():
    """低くまばらなピアノ(Eマイナー、半音ずつ下がっていく)"""
    x = np.zeros(N, np.float32); seq = [52, 55, 59, 58, 52, 55, 57, 56, 51, 55, 58, 57, 50, 53, 57, 56]; t0 = 1.0; i = 0
    while t0 < HIT - 3:
        if not (T_IN < t0 < T_OUT):
            add(x, t0, piano(midi(seq[i % 16])), 0.13)
            if i % 4 == 0: add(x, t0, piano(midi(seq[i % 16] - 12), 6.0), 0.16)
        t0 += 1.7; i += 1
    return x
def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(28), 1.0), (midi(28) * 1.006, 0.8), (midi(40), 0.4), (midi(47), 0.16), (midi(41), 0.08)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    return (x * (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)) * 0.09).astype(np.float32)
def strings():
    t = np.arange(N) / SR
    def cluster(a, b, peak):
        prog = np.clip((t - a) / (b - a), 0, 1); y = np.zeros(N, np.float32)
        for k, n in enumerate([76, 77, 82, 83, 88, 89.5, 94]):
            f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
            y += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
        return y * (ramp(a, b) ** 2 * peak) * (1 - ramp(b - 0.05, b + 0.15))
    return lowpass(cluster(T_IN, T_BUMP, 0.4) + cluster(T_FOG, T_FULL, 0.8) + cluster(T_FULL + 0.4, HIT, 1.0), 5200) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = L['l8']['start']; t0 = a
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
    for k, n in enumerate([64, 65, 70, 71, 76, 77.5, 82, 89]):
        f = midi(n) * (1 - 0.06 * t / 2.4) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t)); ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.3 * np.sign(np.sin(ph))).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.7) + highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + taiko(0.9)[:len(t)]
def resample(x, k):
    """k 倍の高さ・速さにする(声を重ねるとき用)"""
    n = int(len(x) / k); return np.interp(np.arange(n) * k, np.arange(len(x)), x).astype(np.float32)

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    cabin = [reverb_ir(0.35, 1, 3000), reverb_ir(0.35, 2, 3000)]; tun = [reverb_ir(2.6, 3, 2500), reverb_ir(2.6, 4, 2500)]; hall = [reverb_ir(3.6, 5), reverb_ir(3.6, 6)]
    big = np.zeros(N, np.float32); fx = np.zeros(N, np.float32); back = np.zeros(N, np.float32)
    add(big, 0.0, taiko(0.45)); add(fx, T_IN - 0.4, whoosh(1.3), 0.25); add(fx, T_OUT - 0.3, whoosh(1.0), 0.18)
    add(fx, T_BUMP, thud(), 0.55)
    for tp in PRINTS: add(fx, tp, squeak(), 0.35)
    add(big, L['l2']['start'] + 2.0, taiko(0.5)); add(big, T_FULL, taiko(0.95)); add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']:
        if l['id'] == 'v':                                   # 後ろの席から、何人もの声が重なって聞こえる
            v = segs['v']
            for k, d, g in [(1.0, 0.0, 1.0), (0.86, 0.12, 0.8), (1.16, 0.22, 0.7), (0.78, 0.35, 0.6), (1.05, 0.5, 0.5)]: add(back, l['start'] + d, resample(v, k), g)
        elif l['id'] == 'now': add(last, l['start'], segs['now'])
        else: add(nar, l['start'], segs[l['id']])
    allv = nar
    hop = SR // 20; rms = np.sqrt(np.mean(allv[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    inT = ramp(T_IN - 0.3, T_IN + 0.3) * (1 - ramp(T_OUT - 0.3, T_OUT + 0.3))
    eng = engine() * (0.06 + 0.04 * inT) * (1 - ramp(HIT, HIT + 0.15) * 0.8)
    ky = keys(); bedm = drone() * ramp(0, 0.6, 0.35, 1) + strings(); br = breathing(); dz = drizzle() * 0.05; wp = wiper() * 0.5
    hb = heartbeat(); out = []
    for ch in range(2):
        music = (bedm + ky * 0.55 + conv(ky, hall[ch]) * 0.5) * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        car = eng + conv(eng, tun[ch]) * 0.6 * inT + dz + wp + (fx + conv(fx, cabin[ch]) * 0.5)
        breaths = (br if ch == 0 else np.roll(br, 15000)) * 0.05
        voice = nar + conv(nar, cabin[ch]) * 0.03 + (back * 0.7 + conv(back, cabin[ch]) * 0.6 + conv(back, hall[ch]) * 0.25) * 1.2 + last * (1.0 if ch == 0 else 0.55) + conv(last, cabin[ch]) * 0.3
        out.append(music * duck + big + conv(big, hall[ch]) * 0.25 + hb + car + breaths + voice)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([(bedm + ky * 0.55 + conv(ky, hall[c]) * 0.5) * 2.5 for c in range(2)], axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
