# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(97)

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

T_SHADOW = L['l3']['start'] + 1.6            # 障子に影が映る。虫の声が止む
T_DAWN = L['l6']['start'] - 0.25
T_MORNING = L['l7']['start'] - 0.25
T_ONE = L['baba']['end'] - 1.3               # 「布団も敷いてない」
T_NIGHT2 = L['l8']['start'] - 0.25
T_MOVE = L['l8']['end'] + 0.2                # 隣の布団が動く
HIT = L['now']['end'] + 0.5
EV = dict(t_room=L['l2']['start'] - 0.25, t_shoji=L['l3']['start'] - 0.2, shadow=T_SHADOW, t_room2=L['l5']['start'] - 0.25, t_dawn=T_DAWN,
          t_morning=T_MORNING, one=T_ONE, t_night2=T_NIGHT2, move=T_MOVE, hit=HIT)

def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(26), 1.0), (midi(26) * 1.006, 0.8), (midi(38), 0.4), (midi(45), 0.16), (midi(39), 0.08)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)).astype(np.float32)
    return (x * 0.10 + lowpass(rng.standard_normal(N).astype(np.float32), 90) * 0.5).astype(np.float32)
def koto(f, dur=3.5, bend=0.0):
    """琴のような撥弦音。弾いた直後にわずかに音程を押し上げる"""
    t = tt(dur); fb = f * (1 + bend * np.exp(-((t - 0.25) / 0.12) ** 2)); ph = 2 * np.pi * np.cumsum(fb) / SR; x = np.zeros(len(t), np.float32)
    for k in range(1, 13): x += (np.sin(k * ph * np.sqrt(1 + 0.00025 * k * k)) * np.exp(-t * (1.1 + 0.55 * k)) / k ** 0.9 * (1.0 if k % 2 else 0.7)).astype(np.float32)
    x += highpass(rng.standard_normal(len(t)).astype(np.float32), 2000) * np.exp(-t * 180) * 0.6
    x[:48] *= np.linspace(0, 1, 48); return x
def melody():
    """都節音階(D, Eb, G, A, Bb)の、間の多い旋律"""
    x = np.zeros(N, np.float32)
    phrase = [(0, 62), (0.9, 63), (1.8, 62), (3.6, 57), (4.5, 58), (5.4, 57), (7.2, 55), (8.6, 51), (9.5, 50),
              (11.6, 69), (12.5, 70), (13.4, 69), (15.2, 67), (16.1, 63), (17.0, 62), (19.0, 58), (19.9, 57), (21.6, 50)]
    t0 = 0.9
    while t0 < HIT - 3:
        for dt, n in phrase:
            tn = t0 + dt
            if tn > HIT - 3 or T_SHADOW - 0.3 < tn < L['l4']['start'] or T_MOVE - 0.5 < tn: continue      # 影が出ている間は琴も止む
            add(x, tn, koto(midi(n), bend=0.03 if n in (63, 58, 70) else 0.0), 0.2)
            if dt in (0, 11.6): add(x, tn, koto(midi(n - 24), 5.0), 0.22)
        t0 += 23.4
    return x
def insects():
    """鈴虫のような虫の声。影が映ると止み、朝には止んでいる"""
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, rate, ph0, g in [(4180, 0.71, 0.0, 1.0), (4420, 0.53, 1.7, 0.7), (3890, 0.62, 3.1, 0.6)]:
        gate = (np.sin(2 * np.pi * rate * t + ph0) > 0.15).astype(np.float32)
        x += (np.sin(2 * np.pi * f * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 46 * t)) * gate * g).astype(np.float32)
    k = SR // 50; x *= 1  # 包絡をなめらかに
    env = (1 - ramp(T_SHADOW - 0.25, T_SHADOW)) + ramp(L['l4']['start'] + 1.0, L['l4']['start'] + 3.0) * 0.6 * (1 - ramp(T_DAWN + 1.0, T_MORNING)) \
        + ramp(T_NIGHT2, T_NIGHT2 + 0.5) * 0.8 * (1 - ramp(T_MOVE - 0.2, T_MOVE))
    return lowpass(x, 6000) * np.clip(env, 0, 1) * 0.02
def furin(f=2350):
    """風鈴"""
    t = tt(2.5); x = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + 0.5 * np.sin(2 * np.pi * f * 2.71 * t) * np.exp(-t * 4) + 0.3 * np.sin(2 * np.pi * f * 5.2 * t) * np.exp(-t * 7)
    x[:48] *= np.linspace(0, 1, 48); return x.astype(np.float32)
def birds():
    """朝の小鳥"""
    x = np.zeros(N, np.float32); t0 = T_MORNING + 0.3
    while t0 < T_NIGHT2 - 0.5:
        for k in range(int(rng.integers(2, 5))):
            t = tt(0.09); f = rng.uniform(2800, 3600) * (1 + 0.25 * np.sin(np.pi * t / 0.09))
            add(x, t0 + 0.13 * k, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.09) ** 2, 0.5)
        t0 += rng.uniform(0.8, 1.7)
    return x * 0.05
def strings():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    def cluster(a, b, peak):
        prog = np.clip((t - a) / (b - a), 0, 1); y = np.zeros(N, np.float32)
        for k, n in enumerate([74, 75, 80, 81, 86, 87.5, 92]):
            f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
            y += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
        return y * (ramp(a, b) ** 2 * peak) * (1 - ramp(b - 0.05, b + 0.15))
    x = cluster(T_SHADOW, T_DAWN, 0.35) + cluster(T_ONE, HIT, 1.0)
    return lowpass(x, 5200) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    for a, b in [(T_SHADOW + 0.5, T_DAWN - 0.3), (T_NIGHT2, HIT - 0.3)]:
        t0 = a
        while t0 < b:
            p = np.clip((t0 - a) / (b - a), 0, 1); g = 0.35 + 0.65 * p
            add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g); t0 += 0.95 - 0.35 * p
    return x * 0.5
def creak(d=1.1, f0=300):
    t = tt(d); f = f0 * (1 + 0.5 * (t / d) ** 2) * (1 + 0.03 * np.sin(2 * np.pi * 9 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.6 * np.sin(2.02 * ph) + 0.4 * np.sin(3.1 * ph)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * t)))
    return (x * np.sin(np.pi * t / d) ** 1.2).astype(np.float32)
def rustle(d=0.9):
    """布団がこすれる音"""
    t = tt(d); return highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 5000), 1200) * np.sin(np.pi * t / d) ** 2 * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * t))
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

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    hall = [reverb_ir(3.8, 1), reverb_ir(3.8, 2)]; room = [reverb_ir(1.0, 3, 3500), reverb_ir(1.0, 4, 3500)]
    fx = np.zeros(N, np.float32); big = np.zeros(N, np.float32); chime = np.zeros(N, np.float32)
    for tc, g in [(0.6, 0.10), (2.1, 0.05), (L['l2']['start'] + 0.5, 0.08), (L['l2']['start'] + 3.4, 0.05), (T_MORNING + 0.6, 0.07), (T_NIGHT2 + 0.8, 0.05)]:
        add(chime, tc, furin(), g); add(chime, tc + 0.19, furin(2350 * 1.02), g * 0.6)
    add(big, 0.0, taiko(0.6)); add(big, L['rule']['start'] + 2.6, taiko(0.5)); add(big, T_SHADOW, taiko(0.7)); add(big, L['l5']['start'] + 1.2, taiko(0.6)); add(big, T_ONE + 0.9, taiko(0.75))
    add(fx, T_SHADOW - 0.9, creak(1.0, 260), 0.10)          # 廊下の床がきしむ
    add(fx, T_MOVE, rustle(1.0), 0.5); add(fx, T_MOVE + 0.9, rustle(0.7), 0.4)
    add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32); far = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']: add(far if l['id'] == 'call' else last if l['id'] == 'now' else nar, l['start'], segs[l['id']], 1.5 if l['id'] == 'baba' else 1.0)
    far = lowpass(far, 2600) * 1.3                          # 障子ごしの声
    allv = nar + far
    hop = SR // 20; rms = np.sqrt(np.mean(allv[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    mel = melody(); amb = insects() + birds(); bedm = drone() * ramp(0, 0.6, 0.35, 1) * (1 - 0.6 * ramp(T_MORNING, T_MORNING + 0.5) * (1 - ramp(T_ONE, T_ONE + 0.8))) + strings()
    hb = heartbeat(); out = []
    for ch in range(2):
        music = (bedm + mel * 0.5 + conv(mel, hall[ch]) * 0.55) * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        sfx = big + conv(big, hall[ch]) * 0.25 + hb + amb * (1.0 if ch == 0 else 0.85) + chime + conv(chime, hall[ch]) * 0.5 + (fx + conv(fx, room[ch]) * 0.8) * (0.6 if ch == 0 else 1.0)
        voice = nar + conv(nar, room[ch]) * 0.03 + far * 0.6 + conv(far, hall[ch]) * 0.7 + last * (0.7 if ch == 0 else 1.0) + conv(last, hall[ch]) * 0.6
        out.append(music * duck + sfx + voice)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([(bedm + mel * 0.5 + conv(mel, hall[c]) * 0.55) * 2.5 for c in range(2)], axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
