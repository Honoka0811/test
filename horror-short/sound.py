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
rng = np.random.default_rng(13)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tt(d): return np.arange(int(d * SR)) / SR
def add(buf, t0, sig, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf): return
    if i < 0: sig = sig[-i:]; i = 0
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
    """全体長の配列で t0→t1 にかけて v0→v1 に変化する包絡"""
    t = np.arange(N) / SR
    return (v0 + (v1 - v0) * np.clip((t - t0) / max(t1 - t0, 1e-6), 0, 1)).astype(np.float32)

T_RING = L['intro']['end'] + 0.35          # 最初のピンポーン
T_NOTICE = L['notice']['start']
T_DROP = L['inside']['end'] + 0.15         # 無音に落とす
T_VOICE = L['voice']['start']
T_HIT = L['voice']['end'] + 0.25           # ジャンプスケア
T_LOOP = L['loop']['start']

# ---------------- BGM ----------------
def drone():
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    for f, a in [(midi(26), 1.0), (midi(26) * 1.006, 0.8), (midi(38), 0.5), (midi(38) * 0.994, 0.4), (midi(45), 0.16), (midi(39), 0.10)]:
        ph = 2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.07 * t + f)
        x += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)).astype(np.float32)
    x *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)).astype(np.float32)
    rumble = lowpass(rng.standard_normal(N).astype(np.float32), 90) * 6
    return (x * 0.11 + rumble * 0.10).astype(np.float32)

def bell(f, dur=3.5, detune=0.0):
    """オルゴール風の音(わずかに音程が沈む)"""
    t = tt(dur); f = f * (1 + detune)
    bend = 1 - 0.004 * (1 - np.exp(-t * 1.5))
    ph = 2 * np.pi * np.cumsum(f * bend) / SR
    x = np.sin(ph) * np.exp(-t * 1.6) + 0.45 * np.sin(2.76 * ph) * np.exp(-t * 4) + 0.2 * np.sin(5.4 * ph) * np.exp(-t * 8)
    x[:96] *= np.linspace(0, 1, 96)
    return x.astype(np.float32)

def musicbox():
    x = np.zeros(N, np.float32)
    # Dマイナー + 減5度。ゆっくり、ところどころ欠ける子守唄
    motif = [74, 77, 81, 80, 77, 74, 73, 69, 74, 77, 82, 81, 80, 77, 75, 74]
    step = 1.18; t0 = L['intro']['start'] - 0.2; i = 0
    while t0 < T_DROP - 0.5:
        n = motif[i % len(motif)]
        if rng.random() > 0.14:
            add(x, t0 + rng.uniform(-0.03, 0.03), bell(midi(n), detune=rng.uniform(-0.004, 0.004)), 0.20)
            if i % 4 == 0: add(x, t0, bell(midi(n - 24), 4.5), 0.16)
        t0 += step; i += 1
    return x

def strings():
    """不協和なクラスターがゆっくり上昇しながら近づく"""
    t = np.arange(N) / SR; x = np.zeros(N, np.float32)
    prog = np.clip((t - T_NOTICE) / (T_DROP - T_NOTICE), 0, 1)
    for k, n in enumerate([74, 75, 80, 81, 86, 87.5, 92]):
        f = midi(n) * (1 + 0.035 * prog ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (4.5 + k * 0.37) * t + k))
        ph = 2 * np.pi * np.cumsum(f) / SR
        x += ((np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.33 * np.sin(3 * ph)) * (0.6 + 0.4 * np.sin(2 * np.pi * (0.23 + 0.05 * k) * t + k))).astype(np.float32)
    env = ramp(T_NOTICE - 6, T_NOTICE, 0, 0.12) + ramp(T_NOTICE, T_DROP, 0, 0.88) ** 2 * 0.88
    env *= 1 - ramp(T_DROP, T_DROP + 0.12)
    return lowpass(x, 5200) * env * 0.035

def heartbeat():
    x = np.zeros(N, np.float32)
    def thump(f0, g):
        t = tt(0.28); f = f0 * (1 + 1.2 * np.exp(-t * 40))
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * g).astype(np.float32)
    t0 = L['camera']['start'] - 2.5
    while t0 < T_HIT - 0.3:
        p = np.clip((t0 - (L['camera']['start'] - 2.5)) / (T_HIT - L['camera']['start']), 0, 1)
        g = 0.25 + 0.75 * p
        add(x, t0, thump(52, 1.0), g); add(x, t0 + 0.2, thump(44, 0.7), g)
        t0 += 1.05 - 0.42 * p
    return x * 0.5

def static():
    """モニターの砂嵐と小さなクリックノイズ"""
    n = highpass(lowpass(rng.standard_normal(N).astype(np.float32), 6500), 1400)
    hum = np.sin(2 * np.pi * 100 * np.arange(N) / SR).astype(np.float32) * 0.5
    x = n * 0.5 + hum * 0.25
    for _ in range(26):
        t0 = rng.uniform(T_RING + 1, T_DROP); d = int(rng.uniform(0.02, 0.09) * SR)
        add(x, t0, rng.standard_normal(d).astype(np.float32) * np.hanning(d), 1.6)
    env = ramp(T_RING + 0.6, T_RING + 1.0) * (1 - ramp(T_DROP, T_DROP + 0.05))
    return x * env * 0.035

# ---------------- 効果音 ----------------
def chime(pitch=1.0):
    """ピンポーン(少しだけ音程が低く歪んだインターホン)"""
    def tone(f, dur):
        t = tt(dur)
        x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 5) + 0.15 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 9)
        x *= np.exp(-t * 2.6); x[:240] *= np.linspace(0, 1, 240)
        return x.astype(np.float32)
    x = np.zeros(int(2.6 * SR), np.float32)
    add(x, 0, tone(659.3 * pitch, 1.4)); add(x, 0.52, tone(523.3 * pitch, 2.0))
    return x

def boom(g=1.0):
    t = tt(3.0); f = 34 + 50 * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    x += lowpass(rng.standard_normal(len(t)).astype(np.float32), 300) * np.exp(-t * 7) * 2.5
    return (x * g).astype(np.float32)

def stinger():
    """ジャンプスケア: 叩きつけるノイズ + 不協和な叫び声のような倍音"""
    t = tt(2.6); x = np.zeros(len(t), np.float32)
    for k, n in enumerate([62, 63, 68, 69, 74, 75.5, 80, 87]):
        f = midi(n) * (1 - 0.06 * t / 2.6) * (1 + 0.012 * np.sin(2 * np.pi * (6 + k) * t))
        ph = 2 * np.pi * np.cumsum(f) / SR
        x += (np.sin(ph) + 0.6 * np.sign(np.sin(ph)) * 0.5).astype(np.float32)
    x = x / 8 * np.exp(-t * 1.5)
    x += highpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 14) * 0.9
    x[:48] *= np.linspace(0, 1, 48)
    return np.tanh(x * 2.2).astype(np.float32) * 0.8 + boom(0.9)[:len(t)]

def riser(d=1.3):
    """逆再生風の吸い込み音"""
    t = tt(d); x = highpass(rng.standard_normal(len(t)).astype(np.float32), 500) * (t / d) ** 3
    return x

def main():
    wet_ir = [reverb_ir(3.8, 1), reverb_ir(3.8, 2)]
    music = drone() * (ramp(0, 0.6, 0.35, 1) * (1 - ramp(T_DROP, T_DROP + 0.15) * 0.82) * (1 - ramp(DUR - 0.5, DUR) * 0.65))
    mb = musicbox(); st = strings()
    dry_fx = np.zeros(N, np.float32); wet_fx = np.zeros(N, np.float32)
    add(dry_fx, 0.0, boom(0.75))                                   # 冒頭の一撃(フック)
    add(wet_fx, T_RING, chime(), 0.36)
    add(wet_fx, L['repeat']['start'] + 1.1, chime(0.985), 0.17)     # 次の夜
    add(wet_fx, L['repeat']['start'] + 2.7, chime(0.97), 0.17)      # その次の夜
    add(wet_fx, T_NOTICE - 1.15, chime(0.94), 0.20)                 # 4日目
    add(dry_fx, T_DROP - 1.3, riser(), 0.10)
    add(dry_fx, T_DROP, boom(0.6))
    add(dry_fx, T_HIT - 0.35, riser(0.35), 0.16)
    add(dry_fx, T_HIT, stinger(), 0.75)
    add(wet_fx, T_LOOP + 1.2, chime(0.94), 0.14)                    # ループ直前に遠くで鳴る
    hb = heartbeat(); sta = static()
    nar = np.load(os.path.join(HERE, 'output', 'narration.npy'))[:N]
    nar = np.pad(nar, (0, N - len(nar)))
    # 「やっと、気づいてくれた」だけ残響を深くかけ、耳元と遠くの両方から聞こえるようにする
    v = np.zeros(N, np.float32); a, b = int((T_VOICE - 0.1) * SR), int((L['voice']['end'] + 0.1) * SR)
    v[a:b] = nar[a:b]
    # ナレーションに合わせて BGM を下げる
    hop = SR // 20; rms = np.sqrt(np.mean(nar[:N // hop * hop].reshape(-1, hop) ** 2, axis=1)); e = np.zeros_like(rms)
    for i, x in enumerate(rms): e[i] = max(x, (e[i - 1] if i else 0) * 0.9)
    e = np.pad(np.repeat(e, hop), (0, N - len(e) * hop)); duck = 1 - 0.5 * np.clip(e / 0.08, 0, 1)
    duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same').astype(np.float32)
    out = []
    for ch in range(2):
        ir = wet_ir[ch]
        bed = music + st + sta + conv(mb, ir) * 0.5 + mb * 0.5 + conv(st, ir) * 0.5
        fx = dry_fx + hb + wet_fx * 0.8 + conv(wet_fx, ir) * 0.55 + conv(dry_fx, ir) * 0.2
        voice = nar * 0.95 + conv(nar, reverb_ir(1.2, 5 + ch)) * 0.05 + conv(v, ir) * 0.5
        out.append(bed * duck + fx + voice)
    y = np.stack(out, axis=1)
    y[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    y = np.tanh(y / 0.9) * 0.9
    print('peak', float(np.max(np.abs(y))))
    with wave.open(os.path.join(HERE, 'output', 'mix.wav'), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())
    bg = np.stack([music + st + conv(mb, wet_ir[c]) * 0.5 + mb * 0.5 for c in range(2)], axis=1)
    with wave.open(os.path.join(HERE, 'output', 'bgm.wav'), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(bg * 2.5, -1, 1) * 32767).astype(np.int16).tobytes())
    json.dump(dict(ring=T_RING, ring2=L['repeat']['start'] + 1.1, ring3=L['repeat']['start'] + 2.7, ring4=T_NOTICE - 1.15,
                   drop=T_DROP, hit=T_HIT, loop=T_LOOP), open(os.path.join(HERE, 'events.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
