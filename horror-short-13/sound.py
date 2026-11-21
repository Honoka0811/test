# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(199)

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
T_BOW = L['l2']['start'] + dur('l2') * 0.72         # 頭を下げる
T_ALBUM = L['l3']['start'] - 0.25                   # 家でアルバムを開く
FLIPS = [L['l3']['start'] + 1.6, L['l4']['start'] - 0.35, L['l5']['start'] - 0.35, L['l9']['start'] - 0.4]   # ページをめくる
T_P10 = L['l4']['start'] - 0.2                      # 10年前の写真
T_P30 = L['l5']['start'] - 0.2                      # 30年前の写真
T_CMP = L['l6']['start'] - 0.2                      # 2枚を並べて見比べる
G1 = L['l7']['start'] + 0.2                         # 30年前: 見つめる先は祖母
G2 = L['l7']['start'] + dur('l7') * 0.52            # 10年前: 見つめる先は祖父
T_CONC = L['l8']['start'] + 0.2                     # 見つめられた人の遺影が、次の写真に
T_TODAY = L['l9']['start'] - 0.2                    # 今日の集合写真
T_ME = L['l10']['start']                            # 見つめる先は、私
T_TURN = L['now']['start'] - 0.4                    # 写真の中の女の人が、こちらを向く
HIT = L['now']['end'] + 0.5
EV = dict(bow=T_BOW, album=T_ALBUM, flips=FLIPS, p10=T_P10, p30=T_P30, cmp=T_CMP, g1=G1, g2=G2, conc=T_CONC, today=T_TODAY, me=T_ME, turn=T_TURN, hit=HIT)

def orin(f=620, d=7.0):
    """おりん: 長く響く金属の鐘。わずかに違う高さの音が重なって、ゆっくりうなる"""
    t = tt(d); x = np.zeros(len(t), np.float32)
    for k, (m, a, dec) in enumerate([(1.0, 1.0, 0.45), (1.004, 0.8, 0.5), (2.74, 0.45, 0.9), (2.751, 0.35, 0.95), (5.1, 0.18, 1.8), (8.2, 0.08, 3.0)]):
        x += (a * np.sin(2 * np.pi * f * m * t + k) * np.exp(-t * dec)).astype(np.float32)
    x[:120] *= np.linspace(0, 1, 120); return x * 0.5
def mokugyo():
    """木魚: こもった木の音"""
    t = tt(0.25); f = 300 * (1 + 0.25 * np.exp(-t * 60))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28) + lowpass(rng.standard_normal(len(t)).astype(np.float32), 1800) * np.exp(-t * 90) * 0.6).astype(np.float32)
def hall():
    """斎場の音: 木魚の一定のリズムと、低い響き、人のざわめき(焼香の場面だけ)"""
    x = np.zeros(N, np.float32); t0 = 0.6
    while t0 < T_ALBUM - 0.5:
        add(x, t0, mokugyo(), 0.5); t0 += 0.52
    x += lowpass(rng.standard_normal(N).astype(np.float32), 400) * 0.25
    return x * (1 - ramp(T_ALBUM - 0.6, T_ALBUM))
def flip():
    """アルバムの厚紙のページをめくる音"""
    t = tt(0.5); x = highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 5000), 500) * np.sin(np.pi * np.clip(t / 0.35, 0, 1)) ** 1.5
    tk = tt(0.06); add(x, 0.36, (lowpass(rng.standard_normal(len(tk)).astype(np.float32), 1500) * np.exp(-tk * 70)).astype(np.float32), 1.4)
    return x.astype(np.float32)
def roomtone():
    t = np.arange(N) / SR; x = lowpass(rng.standard_normal(N).astype(np.float32), 600) * 0.25
    tk = tt(0.03)
    for k in np.arange(T_ALBUM + 0.5, DUR, 1.0): add(x, k, (np.sin(2 * np.pi * (2300 if int(k) % 2 else 2000) * tk) * np.exp(-tk * 230)).astype(np.float32), 0.3)
    return x * ramp(T_ALBUM - 0.3, T_ALBUM + 0.3)
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
    return lowpass(cluster(L['l1']['start'] + 2, T_ALBUM, 0.35) + cluster(T_P30, T_CONC + 1.5, 0.75) + cluster(T_TODAY, HIT, 1.0), 5200) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = T_CONC; t0 = a
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

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    big_hall = [reverb_ir(3.2, 1, 4000), reverb_ir(3.2, 2, 4000)]; room = [reverb_ir(0.5, 3, 3500), reverb_ir(0.5, 4, 3500)]; hallr = [reverb_ir(3.6, 5), reverb_ir(3.6, 6)]
    big = np.zeros(N, np.float32); fx = np.zeros(N, np.float32); bell = np.zeros(N, np.float32)
    add(bell, 0.3, orin(620), 0.35); add(bell, T_BOW, orin(560, 5), 0.18)
    add(big, T_BOW + 0.1, taiko(0.45))
    for tf in FLIPS: add(fx, tf, flip(), 0.3)
    add(big, T_P10 + 1.4, taiko(0.45)); add(big, T_P30 + 2.6, taiko(0.6))
    add(big, G1, taiko(0.4)); add(big, G2, taiko(0.45)); add(big, T_CONC + 0.4, taiko(0.7))
    add(bell, T_ME + 0.05, orin(500, 7), 0.45); add(big, T_ME, taiko(0.85))
    add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']: add(last if l['id'] == 'now' else nar, l['start'], segs[l['id']])
    hop = SR // 20; rms = np.sqrt(np.mean(nar[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    hl = hall() * 0.06; bedm = drone() * ramp(0, 0.6, 0.35, 1) + strings(); rt = roomtone() * 0.05
    hb = heartbeat(); out = []
    for ch in range(2):
        music = bedm * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        sfx = big + conv(big, hallr[ch]) * 0.25 + hb + hl + conv(hl, big_hall[ch]) * 0.5 + bell * 0.6 + conv(bell, big_hall[ch]) * 0.5 + rt + fx + conv(fx, room[ch]) * 0.3
        voice = nar + conv(nar, room[ch]) * 0.03 + last * (1.0 if ch == 0 else 0.7) + conv(last, room[ch]) * 0.25
        out.append(music * duck + sfx + voice)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([bedm * 2.5] * 2, axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
