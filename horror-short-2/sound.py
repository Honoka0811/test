# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし・権利フリー)、ナレーションとミックスして output/mix.wav を書き出す。"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
DUR = TL['duration']
L = {l['id']: l for l in TL['lines']}
N = int(DUR * SR)
rng = np.random.default_rng(29)

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

SIS = [l for l in TL['lines'] if l['kind'] == 'sis']
ME = [l for l in TL['lines'] if l['kind'] == 'me']
EV = dict(
    knock=L['s7']['end'] + 0.55, knock2=L['door']['start'] - 0.42,
    door_in=L['s7']['end'] + 0.3, door_out=L['s8']['start'] - 0.25,
    buzz=L['door']['end'] + 0.3,
    send=L['away']['end'] + 0.85,                 # 静寂の中ではっきり聞こえる「送信音」
    closet=L['notice']['start'] - 0.25,
    send2=L['s10']['start'] - 0.6,
    hit=L['s10']['end'] + 0.55,
)

# ---------------- BGM ----------------
def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(21), 1.0), (midi(21) * 1.007, 0.8), (midi(33), 0.5), (midi(33) * 0.993, 0.4), (midi(40), 0.15), (midi(34), 0.09)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.06 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.09 * t)).astype(np.float32)
    return (x * 0.11 + lowpass(rng.standard_normal(N).astype(np.float32), 90) * 0.6).astype(np.float32)

def piano(f, dur=5.0):
    t = tt(dur); x = np.zeros(len(t), np.float32)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        x += (np.sin(2 * np.pi * fk * t) * np.exp(-t * (0.7 + 0.45 * k)) / k ** 1.3).astype(np.float32)
    x[:144] *= np.linspace(0, 1, 144)
    return x

def keys():
    """低くまばらなピアノ。Aマイナーに減5度と短2度を混ぜる"""
    x = np.zeros(N, np.float32)
    seq = [45, 52, 51, 48, 45, 53, 52, 46, 45, 52, 57, 56, 51, 48, 46, 45]
    t0 = L['s1']['start'] - 0.6; i = 0
    while t0 < EV['hit'] - 2:
        if not (L['away']['end'] - 0.5 < t0 < EV['closet'] + 0.5):
            n = seq[i % len(seq)]
            add(x, t0, piano(midi(n)), 0.16)
            if i % 4 == 0: add(x, t0, piano(midi(n - 12), 6.0), 0.2)
            if i % 4 == 2: add(x, t0 + 0.9, piano(midi(n + 24), 3.0), 0.05)
        t0 += 1.85; i += 1
    return x

def strings():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    a, b = EV['knock'], EV['hit']
    prog = np.clip((t - a) / (b - a), 0, 1)
    for k, n in enumerate([69, 70, 75, 76, 81, 82.5, 87]):
        f = midi(n) * (1 + 0.04 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k))
        ph = 2 * np.pi * np.cumsum(f) / SR
        x += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
    env = ramp(L['s3']['start'], a, 0, 0.10) + ramp(a, b, 0, 0.9) ** 2 * 0.9
    env *= 1 - ramp(b - 0.05, b + 0.1)
    return lowpass(x, 5200) * env * 0.034

def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40))
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    a = L['away']['start']; t0 = a
    while t0 < EV['hit'] - 0.3:
        p = np.clip((t0 - a) / (EV['hit'] - a), 0, 1); g = 0.3 + 0.7 * p
        add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g)
        t0 += 1.05 - 0.45 * p
    return x * 0.5

# ---------------- 効果音 ----------------
def sfx_send():
    """送信音「シュポッ」"""
    t = tt(0.16); f = 520 * (2.9 ** (t / 0.16))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.16) ** 0.7
    x += highpass(rng.standard_normal(len(t)).astype(np.float32), 2500) * np.exp(-t * 40) * 0.25
    return x.astype(np.float32)
def sfx_recv():
    """受信音「ポコン」"""
    x = np.zeros(int(0.5 * SR), np.float32)
    for dt, f in [(0, 880), (0.11, 1318.5)]:
        t = tt(0.3); add(x, dt, (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 16))
    return x
def sfx_buzz(d=0.9):
    t = tt(d); x = np.sign(np.sin(2 * np.pi * 165 * t)) * 0.5 + np.sin(2 * np.pi * 82 * t)
    x *= (np.sin(np.pi * t / d) ** 0.3) * (0.7 + 0.3 * np.sign(np.sin(2 * np.pi * 2.2 * t + 0.3)))
    return lowpass(x.astype(np.float32), 900)
def sfx_knock():
    t = tt(0.4)
    x = np.sin(2 * np.pi * 150 * t) * np.exp(-t * 34) + 0.6 * np.sin(2 * np.pi * 235 * t) * np.exp(-t * 48)
    x += lowpass(rng.standard_normal(len(t)).astype(np.float32), 1800) * np.exp(-t * 90) * 0.8
    return x.astype(np.float32)
def boom(g=1.0):
    t = tt(3.0); f = 34 + 50 * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    x += lowpass(rng.standard_normal(len(t)).astype(np.float32), 300) * np.exp(-t * 7) * 2.5
    return (x * g).astype(np.float32)
def stinger():
    t = tt(2.4); x = np.zeros(len(t), np.float32)
    for k, n in enumerate([57, 58, 63, 64, 69, 70.5, 75, 82]):
        f = midi(n) * (1 - 0.06 * t / 2.4) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t))
        ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.3 * np.sign(np.sin(ph))).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.7)
    x += highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + boom(0.9)[:len(t)]
def riser(d):
    t = tt(d); return highpass(rng.standard_normal(len(t)).astype(np.float32), 500) * (t / d) ** 3

def main():
    segs = np.load(os.path.join(HERE, 'output', 'segs.npz'))
    hall = [reverb_ir(3.6, 1), reverb_ir(3.6, 2)]
    room = [reverb_ir(0.7, 3, 2500), reverb_ir(0.7, 4, 2500)]
    quiet = 1 - 0.8 * ramp(L['away']['end'] - 0.2, L['away']['end'] + 0.2) * (1 - ramp(EV['closet'], EV['closet'] + 1.5))
    bed = (drone() * ramp(0, 0.6, 0.35, 1) + strings()) * quiet * (1 - ramp(EV['hit'], EV['hit'] + 0.1) * 0.75)
    ky = keys()
    # 効果音: 手元のスマホ(中央)/ クローゼットの中の送信音(こもった音・右寄り)/ ドア(左寄り)
    phone = np.zeros(N, np.float32); muf = np.zeros(N, np.float32); doorfx = np.zeros(N, np.float32); big = np.zeros(N, np.float32)
    add(big, 0.0, boom(0.7)); add(phone, 0.12, sfx_buzz(0.5), 0.10); add(phone, 0.15, sfx_recv(), 0.22)
    for l in SIS:
        add(phone, l['start'] - 0.14, sfx_recv(), 0.20)
        add(muf, l['start'] - 0.55, sfx_send(), 0.22)          # 1通目からずっと鳴っている(伏線)
    for l in ME: add(phone, l['start'] - 0.1, sfx_send(), 0.20)
    add(muf, EV['send'], sfx_send(), 0.75)
    add(muf, EV['send2'], sfx_send(), 0.75)
    for k in (0, 0.3): add(doorfx, EV['knock'] + k, sfx_knock(), 1.0)
    for k in (0, 0.28): add(doorfx, EV['knock2'] + k, sfx_knock(), 0.55)
    add(phone, EV['buzz'], sfx_buzz(0.9), 0.22)
    add(big, EV['hit'] - 0.35, riser(0.35), 0.16); add(big, EV['hit'], stinger(), 0.75)
    add(phone, DUR - 0.75, sfx_recv(), 0.12)                     # ループ直前、もう一通
    muf = lowpass(muf, 850)
    hb = heartbeat()
    # 声
    nar = np.zeros(N, np.float32); door = np.zeros(N, np.float32); last = np.zeros(N, np.float32)
    for l in TL['lines']:
        tgt = door if l['kind'] == 'door' else last if l['id'] == 's10' else nar
        add(tgt, l['start'], segs[l['id']])
    door = lowpass(door, 1100) * 1.6                              # ドア越しのこもった声
    allv = nar + door + last
    hop = SR // 20; rms = np.sqrt(np.mean(allv[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    out = []
    for ch in range(2):
        pan_r = 0.6 if ch == 0 else 1.0; pan_l = 1.0 if ch == 0 else 0.6
        music = bed + ky * 0.55 + conv(ky, hall[ch]) * 0.5
        fx = big + conv(big, hall[ch]) * 0.2 + hb + phone + conv(phone, room[ch]) * 0.25 \
            + (muf + conv(muf, room[ch]) * 0.9) * pan_r + (doorfx + conv(doorfx, room[ch]) * 0.8 + conv(doorfx, hall[ch]) * 0.25) * pan_l
        voice = nar + conv(nar, room[ch]) * 0.04 + (door * 0.7 + conv(door, room[ch]) * 0.7) * pan_l + last * 0.9 + conv(last, hall[ch]) * 0.6
        out.append(music * duck + fx + voice)
    y = np.stack(out, axis=1)
    y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9
    print('peak', float(np.max(np.abs(y))))
    def save(name, a):
        with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    save('mix.wav', y)
    save('bgm.wav', np.stack([(bed + ky * 0.55 + conv(ky, hall[c]) * 0.5) * 2.5 for c in range(2)], axis=1))
    json.dump({k: round(v, 3) for k, v in EV.items()}, open(os.path.join(HERE, 'events.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
