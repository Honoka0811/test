# -*- coding: utf-8 -*-
"""不気味系BGMと効果音をプログラムで合成する(外部音源不要・権利フリー)。
BGM: 半音でうなる低音ドローン + 減和音のパッド + 音程の揺れたオルゴール + 風の音 + 心音 + 長い残響
効果音: 時計の秒針 / 列車の通過とブレーキ音 / 場面転換の低い衝撃音 / 判子の音
単体実行: python3 bgm.py [秒数] [出力wav]
必要: numpy, scipy
"""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR)
    if s < 0: sig, s = sig[-s:], 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def lp(x, f, order=2): return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x).astype(np.float32)
def hp(x, f, order=2): return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x).astype(np.float32)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x).astype(np.float32)

def reverb(x, secs=3.5, mix=0.4, seed=1, damp=3000):
    """指数減衰ノイズのインパルス応答を畳み込む暗めのリバーブ"""
    rng = np.random.default_rng(seed)
    n = int(secs * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n).astype(np.float32) * np.exp(-t / (secs / 6.9))
    ir = lp(ir, damp); ir /= np.sqrt(np.sum(ir ** 2))
    wet = fftconvolve(x, ir)[:len(x)].astype(np.float32)
    return (1 - mix) * x + mix * wet / (np.max(np.abs(wet)) + 1e-9) * np.max(np.abs(x))

def norm(x): return x / (np.max(np.abs(x)) + 1e-9)

# ---------------- BGM ----------------
def drone(total, rng):
    n = int(total * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    # A1 と B♭1 を重ねてうなりを作る + 1 オクターブ上を薄く
    for f, a in ((midi(33), 1.0), (midi(34) * 0.997, 0.55), (midi(45), 0.35), (midi(46) * 1.002, 0.2)):
        wob = 1 + 0.003 * np.sin(2 * np.pi * rng.uniform(0.05, 0.12) * t + rng.uniform(0, 6.28))
        ph = 2 * np.pi * np.cumsum(f * wob) / SR
        sig += a * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph))
    sig *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
    return lp(sig, 400)

def pad(total, rng):
    """A・C・E♭・G♭ の減七和音とその半音上を、ゆっくり膨らませて交互に鳴らす"""
    n = int(total * SR)
    out = np.zeros(n, dtype=np.float32)
    chords = [[57, 60, 63, 66], [58, 61, 64, 67], [57, 60, 63, 68], [56, 59, 62, 65]]
    L = 8.0
    for i in range(int(np.ceil(total / L)) + 1):
        dur = L + 3.0; m = int(dur * SR); t = np.arange(m) / SR
        sig = np.zeros(m, dtype=np.float32)
        for k, note in enumerate(chords[i % 4]):
            f = midi(note - 12)
            for det in (-0.006, 0.0, 0.006):
                ph = 2 * np.pi * f * (1 + det) * t + rng.uniform(0, 6.28)
                sig += (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)) * (0.9 if k else 1.0)
        swell = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
        add(out, i * L - 1.5, sig * swell)
    return lp(out, 1800)

def bell(f, dur, rng, warp=0.0):
    """オルゴール風(非整数倍音) + テープの伸びのような音程の揺れ"""
    n = int(dur * SR); t = np.arange(n) / SR
    wob = 1 + 0.008 * np.sin(2 * np.pi * 5.2 * t) * np.exp(-t / 0.8) - warp * t / dur
    ph = 2 * np.pi * np.cumsum(f * wob) / SR
    sig = (np.sin(ph) * np.exp(-t / 0.9) + 0.45 * np.sin(2.76 * ph) * np.exp(-t / 0.35)
           + 0.2 * np.sin(5.40 * ph) * np.exp(-t / 0.15))
    att = np.minimum(1, t / 0.003)
    return (sig * att).astype(np.float32)

# オルゴールの旋律(MIDI, 拍)。A マイナーを半音でずらした不安定なフレーズ
MELODY = [(81, 1), (80, 1), (76, 1), (77, 2), (75, 1), (72, 1), (71, 3),
          (81, 1), (80, 1), (76, 1), (74, 1), (75, 1), (69, 1), (70, 4)]

def music_box(total, rng, start=4.5, end=65.0, slow_from=None):
    n = int(total * SR); out = np.zeros(n, dtype=np.float32)
    beat = 0.62
    t = start
    while t < end:
        for note, b in MELODY:
            if t >= end: break
            # 後半ほど音程がわずかに狂っていく
            drift = 1 - 0.012 * np.clip((t - 30) / 30, 0, 1) * rng.uniform(0.3, 1.0)
            add(out, t, bell(midi(note) * drift, 2.5, rng, warp=0.01) * rng.uniform(0.6, 1.0))
            t += b * beat
        t += 2 * beat
    return out

def wind(total, rng):
    n = int(total * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    a = bp(x, 250, 900); b = bp(x, 900, 2200)
    m1 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t + 1.0)
    m2 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t + 2.3)
    return a * m1 + 0.35 * b * m2 ** 2

def heartbeat(total, rng, start=34.0, end=65.5):
    n = int(total * SR); out = np.zeros(n, dtype=np.float32)
    t = start
    while t < end:
        k = np.clip((t - start) / (end - start), 0, 1)
        bpm = 58 + 22 * k
        for off, amp in ((0, 1.0), (0.22, 0.65)):
            m = int(0.35 * SR); tt = np.arange(m) / SR
            f = 38 + 30 * np.exp(-tt / 0.03)
            s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.09)
            add(out, t + off, (s * amp * (0.5 + 0.5 * k)).astype(np.float32))
        t += 60 / bpm
    return out

def swell(dur, rng):
    """場面転換前の逆再生風の盛り上がり"""
    n = int(dur * SR); t = np.arange(n) / SR
    x = bp(rng.standard_normal(n).astype(np.float32), 400, 3000)
    tone = np.sin(2 * np.pi * midi(69) * t) + np.sin(2 * np.pi * midi(70) * t)
    return ((0.6 * x + 0.4 * tone) * (t / dur) ** 3).astype(np.float32)

SCENE_STARTS = [7, 16.5, 25, 34, 47, 57, 66]

def generate(total, seed=13):
    rng = np.random.default_rng(seed)
    n = int(total * SR); t = np.arange(n) / SR
    d = norm(drone(total, rng)); p = norm(pad(total, rng))
    mb = norm(reverb(music_box(total, rng), 3.0, 0.55, seed=2, damp=5000))
    w = norm(wind(total, rng)); hb = norm(heartbeat(total, rng))
    sw = np.zeros(n, dtype=np.float32)
    for s in SCENE_STARTS:
        add(sw, s - 1.6, swell(1.6, rng))
    sw = norm(sw)
    # 最後の場面ではオルゴール以外を落とし、静けさを強調
    end_duck = 1 - 0.75 * np.clip((t - 65.5) / 1.0, 0, 1)
    mix = (0.55 * d + 0.30 * p) * end_duck + 0.30 * mb + 0.14 * w + 0.55 * hb + 0.18 * sw
    mix = reverb(mix, 4.0, 0.25, seed=3, damp=2500)
    mix *= env_ar(n, 2.5, 4.0)
    return (norm(mix) * 0.9).astype(np.float32)

# ---------------- 効果音 ----------------
def boom(rng, dur=2.5):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 30 + 70 * np.exp(-t / 0.15)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.6)
    noise = lp(rng.standard_normal(n).astype(np.float32), 600) * np.exp(-t / 0.25)
    return reverb((body + 0.5 * norm(noise)).astype(np.float32), 3.0, 0.35, seed=5)

def tick(rng, hi=True):
    n = int(0.05 * SR); t = np.arange(n) / SR
    x = hp(rng.standard_normal(n).astype(np.float32), 2500) * np.exp(-t / 0.004)
    x += 0.5 * np.sin(2 * np.pi * (3200 if hi else 2600) * t) * np.exp(-t / 0.006)
    return x.astype(np.float32)

def stamp(rng):
    n = int(0.4 * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(90 + 120 * np.exp(-t / 0.01)) / SR) * np.exp(-t / 0.05)
    click = lp(rng.standard_normal(n).astype(np.float32), 3000) * np.exp(-t / 0.008)
    return (body + 0.6 * click).astype(np.float32)

def train(rng, dur=5.5):
    """遠くから近づいて通り過ぎる列車(ジョイント音のリズム + 走行ノイズ + ブレーキの軋み)"""
    n = int(dur * SR); t = np.arange(n) / SR
    rumble = lp(rng.standard_normal(n).astype(np.float32), 180, 4)
    rumble += 0.3 * bp(rng.standard_normal(n).astype(np.float32), 300, 1200)
    clack = np.zeros(n, dtype=np.float32)
    for k, ts in enumerate(np.arange(0.2, dur - 0.3, 0.42)):
        for off in (0, 0.11):
            m = int(0.12 * SR); tt = np.arange(m) / SR
            c = lp(rng.standard_normal(m).astype(np.float32), 900) * np.exp(-tt / 0.02)
            add(clack, ts + off, c)
    # 近づいて遠ざかる音量(ピーク 2.2 秒)
    pass_env = np.exp(-((t - 2.2) / 1.3) ** 2)
    # ブレーキの軋み(高音、ゆらぐ)
    sq_f = 2800 + 250 * np.sin(2 * np.pi * 7 * t) - 300 * t / dur
    squeal = np.sin(2 * np.pi * np.cumsum(sq_f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(sq_f * 1.51) / SR)
    sq_env = np.clip((t - 1.4) / 0.4, 0, 1) * np.clip((dur - 0.6 - t) / 1.5, 0, 1)
    x = (norm(rumble) * 0.8 + norm(clack) * 0.9) * pass_env + 0.22 * squeal * sq_env
    return reverb(x.astype(np.float32), 2.5, 0.3, seed=7)

def sfx(total, seed=21):
    rng = np.random.default_rng(seed)
    n = int(total * SR); out = np.zeros(n, dtype=np.float32)
    add(out, 0.25, boom(rng) * 0.9)
    # 時計の秒針(7〜16 秒)
    for i, ts in enumerate(np.arange(7.3, 16.2, 1.0)):
        add(out, ts, tick(rng, i % 2 == 0) * 0.35)
    add(out, 13.0, stamp(rng) * 0.8)          # 「消息不明」の判子
    add(out, 25.0, train(rng) * 0.75)          # 列車
    for s in (34.0, 47.0, 57.0):
        add(out, s + 0.05, boom(rng, 2.0) * 0.55)
    add(out, 66.0, boom(rng, 3.5) * 0.9)
    add(out, 63.5, stamp(rng) * 0.6)          # 「時効」の判子
    return out

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 72.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
