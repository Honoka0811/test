# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
L = {l['id']: l for l in TL['lines']}
DUR = TL['duration']; N = int(DUR * SR)
rng = np.random.default_rng(214)

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

def dur(k): return L[k]['end'] - L[k]['start']
def at(k, r): return L[k]['start'] + dur(k) * r
T_LOCK = at('l4', 0.05)                              # 玄関の鍵(かかったまま)
T_ROOM = at('l4', 0.5)                               # 家じゅうを探す
T_COP = L['l5']['start'] - 0.2                       # 外で、おまわりさんが足あとを見る
T_TOE = L['l6']['start'] + 0.2                       # 足あとのアップ: つま先は道路を向いている
T_MAP = L['l7']['start'] - 0.2                       # 上から見た図
T_FLIP = at('l7', 0.55)                              # 矢印が逆になる: 出ていった
T_NIGHT = L['l9']['start'] - 0.2                     # ゆうべの家(雪が降っている)
T_SIL = at('l10', 0.22)                              # 暗い1階の窓に、人影
T_OUT = at('l10', 0.6)                               # 玄関から出ていく
T_KEY = L['l11']['start'] - 0.3                      # 外から合いかぎで鍵をかける
T_BACK = L['l12']['start'] - 0.2                     # 次の朝、家へ戻る
T_SEE = L['l13']['start'] - 0.2                      # また足あと
T_TOE2 = L['l14']['start'] + 0.3                     # つま先は家を向いている
T_PHONE = L['l15']['start'] - 0.1                    # 外から電話しようとする
T_OPEN = at('l15', 0.62)                             # 玄関の引き戸が、内側から開く
HIT = L['l16']['end'] + 0.4
T_HAND = L['l1b']['start'] - 0.2                     # 不動産屋の担当者が、鍵を3本わたす
T_MEMO = L['l16']['start'] - 0.1                     # あの声は…
STEPS_OUT = [T_KEY + 1.45 + k * 0.5 for k in range(3)]          # 鍵をかけて、雪の上を歩いていく
STEPS_ME = [at('l12', 0.62) + k * 0.55 for k in range(9)]       # 次の朝、私が家まで歩く
EV = dict(hand=T_HAND, memo=T_MEMO, lock=T_LOCK, room=T_ROOM, cop=T_COP, toe=T_TOE, map=T_MAP, flip=T_FLIP, night=T_NIGHT, sil=T_SIL, out=T_OUT, key=T_KEY, back=T_BACK, see=T_SEE, toe2=T_TOE2, phone=T_PHONE, open=T_OPEN, hit=HIT, stepsOut=STEPS_OUT, stepsMe=STEPS_ME)

def noise(n, seed=None): return (np.random.default_rng(seed).standard_normal(n) if seed is not None else rng.standard_normal(n)).astype(np.float32)
def wind():
    """外の風: 低いノイズが、ゆっくり強くなったり弱くなったりする"""
    t = np.arange(N) / SR; g = 0.55 + 0.45 * np.sin(2 * np.pi * 0.09 * t) * np.sin(2 * np.pi * 0.031 * t + 1)
    return (lowpass(highpass(noise(N), 120), 900) * g + lowpass(noise(N), 250) * 0.6).astype(np.float32)
def crunch(g=1.0):
    """雪を踏む音: きゅっ、ぎゅっ と細かくつぶれる"""
    t = tt(0.32); x = np.zeros(len(t), np.float32); r = np.random.default_rng(int(rng.integers(1e9)))
    for k in range(int(40 + r.integers(20))):
        i = int(r.uniform(0, 0.22) * SR); n = int(r.uniform(0.002, 0.008) * SR); x[i:i + n] += r.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / (n / 3)) * r.uniform(0.3, 1)
    x = lowpass(highpass(x, 400), 3500) + lowpass(noise(len(t)), 400) * np.exp(-t * 18) * 0.5
    return (x * np.sin(np.pi * np.clip(t / 0.3, 0, 1)) ** 0.5 * g).astype(np.float32)
def click(f=2600):
    """鍵(サムターン)の金属音: かちゃ"""
    t = tt(0.12); x = (np.sin(2 * np.pi * f * t) * 0.5 + highpass(noise(len(t)), 2000)) * np.exp(-t * 70)
    t2 = tt(0.08); y = np.zeros(len(t), np.float32); y[int(0.035 * SR):int(0.035 * SR) + len(t2)] += (np.sin(2 * np.pi * f * 1.3 * t2) * 0.4 + highpass(noise(len(t2)), 2500)) * np.exp(-t2 * 90)
    return (x + y * 0.8).astype(np.float32)
def keys():
    """鍵束がふれあう音と、鍵穴に差しこんで回す音"""
    x = np.zeros(int(1.4 * SR), np.float32)
    for k in range(7):
        t = tt(0.25); f = rng.uniform(3500, 6500); add(x, 0.05 + k * 0.06 + rng.uniform(0, 0.03), (np.sin(2 * np.pi * f * t) * np.exp(-t * 40) * rng.uniform(0.2, 0.5)).astype(np.float32))
    t = tt(0.3); add(x, 0.65, (lowpass(highpass(noise(len(t)), 1500), 6000) * np.sin(np.pi * t / 0.3) * 0.5).astype(np.float32)); add(x, 1.05, click(2200), 1.2)
    return x
def slidedoor(d=1.8):
    """古い玄関の引き戸を、ゆっくり開ける音: レールの上で、がらがら…と細かく揺れる"""
    t = tt(d); r = 0.5 + 0.5 * np.sin(2 * np.pi * 23 * t + 3 * np.sin(2 * np.pi * 2.1 * t))
    x = lowpass(highpass(noise(len(t)), 150), 1500) * (0.4 + 0.6 * r ** 3) + np.sin(2 * np.pi * 95 * t) * 0.15 * r
    rattle = highpass(noise(len(t)), 2500) * (r > 0.92) * 0.6                       # すりガラスがかたかた鳴る
    return ((x + rattle) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.6).astype(np.float32)
def tap():
    t = tt(0.04); return (highpass(noise(len(t)), 1500) * np.exp(-t * 150) * 0.6).astype(np.float32)
def creak(d=1.0, f0=140):
    t = tt(d); f = f0 * (1 + 0.25 * np.sin(2 * np.pi * 0.7 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sign(np.sin(ph)) * (0.5 + 0.5 * np.sin(2 * np.pi * 31 * t)) ** 4
    return (lowpass(x.astype(np.float32), 1500) * np.sin(np.pi * t / d) * 0.6).astype(np.float32)
def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(26), 1.0), (midi(26) * 1.006, 0.8), (midi(38), 0.4), (midi(45), 0.16), (midi(39), 0.07)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    return (x * (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)) * 0.09).astype(np.float32)
def strings():
    t = np.arange(N) / SR
    def cluster(a, b, peak):
        prog = np.clip((t - a) / (b - a), 0, 1); y = np.zeros(N, np.float32)
        for k, n in enumerate([74, 75, 80, 81, 86, 87.5, 92]):
            f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
            y += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
        return y * (ramp(a, b) ** 2 * peak) * (1 - ramp(b - 0.05, b + 0.15))
    return lowpass(cluster(L['l3']['start'], T_COP, 0.35) + cluster(T_FLIP, T_KEY + 1.5, 0.75) + cluster(T_SEE, HIT, 1.0), 5200) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = T_SEE; t0 = a
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

def resample(x, k):
    n = int(len(x) / k); return np.interp(np.arange(n) * k, np.arange(len(x)), x).astype(np.float32)

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    room = [reverb_ir(0.5, 3, 3500), reverb_ir(0.5, 4, 3500)]; snow = [reverb_ir(0.25, 5, 3000), reverb_ir(0.25, 6, 3000)]; hallr = [reverb_ir(3.0, 7), reverb_ir(3.0, 8)]; house = [reverb_ir(1.0, 9, 2000), reverb_ir(1.0, 10, 2000)]
    big = np.zeros(N, np.float32); fx = np.zeros(N, np.float32)
    add(big, 0.2, taiko(0.4)); add(big, L['l3']['start'] + 1.6, taiko(0.5))
    add(fx, T_LOCK + 0.5, click(), 0.25)                                         # 鍵を確かめる
    add(fx, T_ROOM + 0.2, creak(0.9, 120), 0.12)                                 # 家の中を歩く床のきしみ
    for k in range(4): add(fx, T_COP + 0.3 + k * 0.6, crunch(0.6))              # おまわりさんが足あとの横へ
    add(big, T_TOE + 0.3, taiko(0.55)); add(big, T_FLIP, taiko(0.75))
    for k in range(3): add(fx, L['l10']['start'] + 0.2 + k * 1.3, creak(0.7, 150 + k * 10), 0.08)   # ゆうべ、家の中で
    add(fx, T_OUT + 0.1, slidedoor(1.2), 0.25)
    for s in STEPS_OUT: add(fx, s, crunch(0.45))
    add(fx, T_KEY, keys(), 0.4); add(big, T_KEY + 1.05, taiko(0.6))
    for s in STEPS_ME: add(fx, s, crunch(0.7))
    add(big, T_SEE + 0.3, taiko(0.5)); add(big, T_TOE2 + 0.3, taiko(0.8))
    for k in range(3): add(fx, T_PHONE + 0.8 + k * 0.28, tap(), 0.5)             # 電話の画面を押す
    add(fx, T_OPEN, slidedoor(2.2), 0.55); add(big, T_OPEN + 0.2, taiko(0.6))
    add(fx, T_HAND + 1.6, keys()[:int(0.6 * SR)], 0.35)                              # 机に置かれる鍵束
    add(big, T_MEMO + 0.1, taiko(0.8))
    add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']:
        if l['id'] == 'now': add(last, l['start'], segs['now'])                 # narrate.py で低くした男の声
        else: add(nar, l['start'], segs[l['id']])
    last = lowpass(last, 3200) * 1.1
    hop = SR // 20; rms = np.sqrt(np.mean(nar[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    # 外の場面は風、家の中は静か
    outside = np.clip(ramp(0, 0.1) - ramp(T_LOCK - 0.3, T_LOCK) + ramp(T_COP - 0.3, T_COP) - ramp(T_MAP - 0.3, T_MAP) + ramp(T_NIGHT - 0.3, T_NIGHT) * 0.7 - ramp(T_KEY + 1.6, T_KEY + 2.0) * 0.7 + ramp(T_BACK - 0.3, T_BACK) - ramp(HIT, HIT + 0.05), 0, 1)
    wd = wind() * (0.08 * outside + 0.015); bedm = drone() * ramp(0, 0.6, 0.35, 1) + strings(); hb = heartbeat(); out = []
    for ch in range(2):
        music = bedm * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        sfx = big + conv(big, hallr[ch]) * 0.25 + hb + wd * (1.0 if ch == 0 else 0.85) + fx + conv(fx, snow[ch]) * 0.3
        voice = nar + conv(nar, room[ch]) * 0.03 + last * (0.9 if ch == 0 else 0.8) + conv(last, house[ch]) * 0.35
        out.append(music * duck + sfx + voice)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))), 'dur', DUR)
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([bedm * 2.5] * 2, axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
