# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし)、ナレーションとミックスして output/mix.wav を書き出す。
効果音のタイミングを events.json に書き出し、映像と同期させる。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; FPS = 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']; L = {l['id']: l for l in TL['lines']}; N = int(DUR * SR)
rng = np.random.default_rng(113)

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

FOUND = [L['l3']['start'] + 0.15, L['l3']['start'] + 0.95, L['l3']['start'] + 1.8]
cd = L['cnt']['end'] - L['cnt']['start']
COUNT = [L['cnt']['start'] + cd * k for k in (0.03, 0.29, 0.55, 0.80)]
T_FIVE = L['go']['start']
T_STOP = L['go']['end'] + 0.3                 # みんなの足が止まる
HIT = L['now']['end'] + 0.5
EV = dict(t_oni=L['call']['start'] - 0.45, replies=[L[k]['start'] for k in ('r1', 'r2', 'r3')], found=FOUND, t_dusk=L['l4']['start'] - 0.25, extra=L['extra']['start'],
          t_run=L['l6']['start'] - 0.2, t_road=L['l7']['start'] - 0.3, count=COUNT, five=T_FIVE, stop=T_STOP, hit=HIT)

def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(24), 1.0), (midi(24) * 1.006, 0.8), (midi(36), 0.4), (midi(43), 0.16), (midi(37), 0.07)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.05 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)).astype(np.float32)
    return (x * 0.10 + lowpass(rng.standard_normal(N).astype(np.float32), 90) * 0.5).astype(np.float32)
def chime_note(f, dur=3.2):
    t = tt(dur); x = np.sin(2 * np.pi * f * t) * np.exp(-t * 1.3) + 0.35 * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t * 2.6) + 0.18 * np.sin(2 * np.pi * 4.07 * f * t) * np.exp(-t * 5)
    x[:240] *= np.linspace(0, 1, 240); return x.astype(np.float32)
def town_chime():
    """夕方5時に遠くのスピーカーから流れるチャイム風の旋律(自作・ヨナ抜き音階)。後半は音程が少しずつ下がっていく"""
    x = np.zeros(N, np.float32)
    phrase = [(0, 67), (1, 69), (2, 72), (3.5, 69), (4.5, 67), (5.5, 64), (7, 62), (8, 64), (9, 67), (10.5, 64), (11.5, 62), (12.5, 60),
              (14.5, 72), (15.5, 74), (16.5, 76), (18, 72), (19, 69), (20, 67), (21.5, 69), (22.5, 67), (23.5, 64), (25, 62), (26, 60)]
    beat = 0.62; t0 = 0.8
    while t0 < HIT - 3:
        for b, n in phrase:
            tn = t0 + b * beat
            if tn > T_FIVE - 0.4: continue
            sag = 1 - 0.035 * max(0.0, (tn - L['l4']['start']) / (T_FIVE - L['l4']['start'])) ** 2        # 日が暮れると、少しずつ狂う
            add(x, tn, chime_note(midi(n) * sag), 0.16)
        t0 += 28.5 * beat
    # 遠くのスピーカーらしい、遅れて重なるこだま
    y = x.copy()
    for d, g in [(0.37, 0.5), (0.81, 0.3), (1.29, 0.16)]:
        k = int(d * SR); y[k:] += x[:-k] * g
    return lowpass(highpass(y, 300), 2800)
def higurashi():
    """ひぐらしのような「カナカナ…」。日が暮れると鳴きやむ"""
    x = np.zeros(N, np.float32); t0 = 0.3
    while t0 < L['l4']['end']:
        n = int(rng.integers(9, 15)); f0 = rng.uniform(3300, 3700); g = rng.uniform(0.5, 1.0)
        for k in range(n):
            t = tt(0.13); f = f0 * (1 - 0.012 * k) * (1 + 0.04 * np.sin(2 * np.pi * 9 * t))
            add(x, t0 + 0.155 * k * (1 + 0.02 * k), np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.13) ** 1.5 * (0.5 + 0.5 * np.sin(2 * np.pi * 120 * t)), g * (1 - 0.05 * k))
        t0 += rng.uniform(2.6, 4.2)
    return x * (1 - ramp(L['l4']['start'], L['l4']['end'])) * 0.035
def crow():
    t = tt(0.42); f = 620 * (1 - 0.25 * t / 0.42) * (1 + 0.03 * np.sin(2 * np.pi * 31 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sign(np.sin(ph)) * 0.5 + np.sin(ph) + 0.5 * np.sin(3 * ph)) * np.sin(np.pi * t / 0.42) ** 0.6
    return lowpass(highpass(x.astype(np.float32), 500), 2600)
def gravel(g=1.0):
    """砂利や土を踏む足音"""
    t = tt(0.16); return highpass(lowpass(rng.standard_normal(len(t)).astype(np.float32), 4200), 700) * np.exp(-t * 26) * g
def wind():
    x = lowpass(rng.standard_normal(N).astype(np.float32), 500); t = np.arange(N) / SR
    return x * (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t + 1)) * (ramp(L['l4']['start'], L['extra']['start'], 0, 1) * (1 - ramp(EV['t_road'], EV['t_road'] + 1) * 0.6)) * 0.5
def strings():
    t = np.arange(N) / SR
    def cluster(a, b, peak):
        prog = np.clip((t - a) / (b - a), 0, 1); y = np.zeros(N, np.float32)
        for k, n in enumerate([72, 73, 78, 79, 84, 85.5, 90]):
            f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k)); ph = 2 * np.pi * np.cumsum(f) / SR
            y += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
        return y * (ramp(a, b) ** 2 * peak) * (1 - ramp(b - 0.05, b + 0.15))
    return lowpass(cluster(L['extra']['start'] - 0.5, EV['t_road'], 0.45) + cluster(L['l8']['start'], HIT, 1.0), 5200) * 0.034
def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40)); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    for a, b, s in [(L['extra']['end'], EV['t_road'], 0.7), (T_FIVE, HIT - 0.3, 0.9)]:
        t0 = a
        while t0 < b:
            p = np.clip((t0 - a) / (b - a), 0, 1); g = 0.4 + 0.6 * p
            add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g); t0 += s - 0.3 * p
    return x * 0.5
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
def tick():
    t = tt(0.05); return (np.sin(2 * np.pi * 1300 * t) * np.exp(-t * 110)).astype(np.float32)

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    hall = [reverb_ir(3.8, 1), reverb_ir(3.8, 2)]; yard = [reverb_ir(1.6, 3, 3000), reverb_ir(1.6, 4, 3000)]
    big = np.zeros(N, np.float32); stepsL = np.zeros(N, np.float32); stepsR = np.zeros(N, np.float32); birdsfx = np.zeros(N, np.float32); ui = np.zeros(N, np.float32)
    for tc in (2.2, 9.4, 26.4): add(birdsfx, tc, crow(), 0.06); add(birdsfx, tc + 0.55, crow(), 0.05)
    add(big, 0.0, taiko(0.6)); add(big, L['extra']['start'] - 0.1, taiko(0.75)); add(big, T_FIVE, taiko(0.9))
    for tf in FOUND: add(stepsL if tf == FOUND[1] else stepsR, tf, gravel(0.5), 0.5)
    t0 = EV['t_run']                                             # 走って逃げる
    while t0 < EV['t_road'] - 0.2:
        add(stepsL, t0, gravel(), 0.5); add(stepsR, t0 + 0.11, gravel(), 0.45); add(stepsL, t0 + 0.17, gravel(), 0.4); t0 += 0.24
    t0 = EV['t_road'] + 0.2; k = 0                               # 帰り道を歩く。4人ぶんの足音
    while t0 < T_STOP:
        add(stepsL if k % 2 else stepsR, t0, gravel(), 0.22 + 0.06 * rng.random()); add(stepsR if k % 2 else stepsL, t0 + 0.09, gravel(), 0.16); add(stepsL, t0 + 0.21, gravel(), 0.14); t0 += 0.3; k += 1
    t0 = T_STOP + 0.5                                            # みんなが止まったあとも、ひとりぶんだけ足音が近づく
    while t0 < HIT - 0.2:
        add(stepsR, t0, gravel(), 0.4); t0 += 0.62
    for tcnt in COUNT: add(ui, tcnt, tick(), 0.12)
    add(big, HIT, stinger(), 0.75)
    nar = np.zeros(N, np.float32); kids = [np.zeros(N, np.float32) for _ in range(3)]; far = np.zeros(N, np.float32); last = np.zeros(N, np.float32); me = np.zeros(N, np.float32)
    for l in TL['lines']:
        tgt = {'r1': kids[0], 'r2': kids[1], 'r3': kids[2], 'extra': far, 'now': last, 'call': me}.get(l['id'], nar); add(tgt, l['start'], segs[l['id']])
    far = lowpass(far, 1800) * 1.4
    kids = [lowpass(k, 3200) for k in kids]
    allv = nar + me
    hop = SR // 20; rms = np.sqrt(np.mean(allv[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    ch_ = town_chime(); amb = higurashi() + birdsfx; wn = wind()
    hush = 1 - 0.85 * ramp(L['extra']['start'] - 0.4, L['extra']['start']) * (1 - ramp(L['l5']['start'], L['l5']['start'] + 1.0))     # 声がした瞬間、すべてが静まる
    bedm = drone() * ramp(0, 0.6, 0.35, 1) + strings()
    hb = heartbeat(); out = []
    pans = [(1.0, 0.45), (0.5, 1.0), (0.85, 0.85)]
    for ch in range(2):
        music = (bedm + (ch_ * 0.6 + conv(ch_, hall[ch]) * 0.5) * hush) * (1 - ramp(HIT, HIT + 0.1) * 0.75)
        sfx = big + conv(big, hall[ch]) * 0.25 + hb + ui + (amb + conv(amb, yard[ch]) * 0.5) * hush + wn * (1.0 if ch == 0 else 0.8) + (stepsL if ch == 0 else stepsR) + (stepsR if ch == 0 else stepsL) * 0.45
        voice = nar + conv(nar, yard[ch]) * 0.03 + me * 0.9 + conv(me, yard[ch]) * 0.5
        for k in range(3): voice = voice + (kids[k] * 0.5 + conv(kids[k], yard[ch]) * 0.7) * pans[k][ch]
        voice = voice + far * 0.3 + conv(far, hall[ch]) * 0.5 + last * (0.7 if ch == 0 else 1.0) + conv(last, hall[ch]) * 0.6
        out.append(music * duck + sfx + voice)
    y = np.stack(out, axis=1); y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9; print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y); save('bgm.wav', np.stack([(bedm + ch_ * 0.6 + conv(ch_, hall[c]) * 0.5) * 2.5 for c in range(2)], axis=1))
    json.dump(EV, open(os.path.join(HERE, 'events.json'), 'w'))

if __name__ == '__main__':
    main()
