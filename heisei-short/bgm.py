# -*- coding: utf-8 -*-
"""平成J-POP/ユーロビート風のBGMを numpy だけで合成する(外部音源なし・権利フリー)。
126BPM / 王道進行(F→G→Em→Am)。4つ打ち + 裏打ちベース + デチューンしたシンセのコード + 着メロ風のピコピコリード。
冒頭0秒からいきなり鳴らして掴む → ノストラダムス場面はドラムを抜いて不穏に → 「しなかった」で再ドロップ。
"""
import numpy as np

SR = 48000
BPM = 126
BEAT = 60 / BPM
BAR = BEAT * 4
# 王道進行(IV-V-iii-vi)、キーC
PROG = [[53, 57, 60, 64], [55, 59, 62, 65], [52, 55, 59, 64], [57, 60, 64, 67]]  # Fmaj7 / G7 / Em7 / Am7
ROOT = [41, 43, 40, 45]
# 着メロ風リード(16分音符単位, 1小節=16, None=休符)。2小節フレーズ×2
LEAD = [
    [72, None, 76, None, 79, None, 77, 76, None, 74, None, 72, 74, None, 76, None],
    [74, None, 79, None, 83, None, 81, 79, None, 77, None, 76, 74, None, 71, None],
    [71, None, 76, None, 79, None, 83, 84, None, 83, None, 79, 76, None, 79, None],
    [81, None, 79, None, 76, None, 72, 74, None, 76, None, 72, 69, None, None, None],
]

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def add(buf, t, sig, gain=1.0):
    s = int(t * SR)
    if s >= len(buf) or s < 0: return
    e = min(len(buf), s + len(sig)); buf[s:e] += sig[:e - s] * gain

def env(n, a=0.005, d=0.1, s=0.6, r=0.05):
    t = np.arange(n) / SR
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / d))
    nr = min(n, int(r * SR)); e[n - nr:] *= np.linspace(1, 0, nr)
    return e.astype(np.float32)

def saw(f, n, phase=0.0):
    t = np.arange(n) / SR; out = np.zeros(n, np.float32)
    for k in range(1, int(min(40, 9000 / f)) + 1):
        out += np.sin(2 * np.pi * f * k * t + phase * k) / k
    return out * 0.6

def square(f, n):
    t = np.arange(n) / SR; out = np.zeros(n, np.float32)
    for k in range(1, int(min(25, 9000 / f)) + 1, 2):
        out += np.sin(2 * np.pi * f * k * t) / k
    return out * 0.8

def kick():
    n = int(0.32 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)).astype(np.float32)

def noise_hit(dur, decay, rng, hp=True):
    n = int(dur * SR); x = rng.standard_normal(n).astype(np.float32)
    if hp: x = np.diff(x, prepend=0) * 0.6
    return x * np.exp(-np.arange(n) / SR / decay).astype(np.float32)

def clap(rng):
    x = noise_hit(0.25, 0.06, rng)
    x = np.convolve(x, np.ones(6) / 6, 'same')
    e = np.ones_like(x);
    for o in (0, 0.012, 0.024): e[int(o * SR):int(o * SR) + 200] *= 1.6
    return x * e

def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, 'same').astype(np.float32)

def generate(total, tension=None, seed=3):
    """tension=(開始秒, 終了秒): その間はドラム・リードを抜き、低音の不穏なパッドにする"""
    rng = np.random.default_rng(seed)
    N = int(total * SR) + SR
    drums = np.zeros(N, np.float32); bass = np.zeros(N, np.float32)
    chords = np.zeros(N, np.float32); lead = np.zeros(N, np.float32); fx = np.zeros(N, np.float32)
    K = kick();
    t0s, t1s = tension if tension else (1e9, 1e9)
    nbar = int(np.ceil(total / BAR)) + 1
    for b in range(nbar):
        bt = b * BAR; ci = b % 4; ch = PROG[ci]
        for q in range(16):
            t = bt + q * BEAT / 4
            if t >= total: break
            calm = t0s <= t < t1s
            if calm:
                continue
            if q % 4 == 0: add(drums, t, K, 1.0)
            if q % 4 == 2: add(drums, t, noise_hit(0.12, 0.03, rng), 0.22)          # 裏のオープンハット
            if q % 2 == 1: add(drums, t, noise_hit(0.04, 0.008, rng), 0.12)         # 16分ハット
            if q in (4, 12): add(drums, t, clap(rng), 0.35)
            # 裏打ちオクターブベース
            if q % 2 == 0:
                m = ROOT[ci] + (12 if q % 4 == 2 else 0)
                n = int(BEAT / 2 * SR * 0.9)
                add(bass, t, lowpass(saw(hz(m), n), 8) * env(n, 0.003, 0.08, 0.35, 0.02), 1.0)
            # シンセのコード(裏拍スタブ)
            if q % 4 == 2:
                n = int(BEAT * 0.45 * SR)
                sig = sum(saw(hz(m) * (1 + d), n, rng.uniform(0, 6)) for m in ch for d in (-0.006, 0.006))
                add(chords, t, lowpass(sig, 3) * env(n, 0.002, 0.07, 0.25, 0.03), 1.0)
            # 着メロ風リード
            ph = LEAD[b % 4][q]
            if ph is not None:
                n = int(BEAT / 4 * SR * 1.6)
                add(lead, t, square(hz(ph), n) * env(n, 0.002, 0.06, 0.3, 0.03), 1.0)
    # 不穏区間: 低いドローン + 上昇するノイズ(ライザー)
    if tension:
        n = int((t1s - t0s) * SR); tt = np.arange(n) / SR
        drone = (saw(hz(33), n) + saw(hz(33.5), n) * 0.8) * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * tt))
        drone = lowpass(drone, 20) * np.minimum(1, tt / 0.3)
        add(fx, t0s, drone.astype(np.float32), 0.9)
        riser = rng.standard_normal(n).astype(np.float32) * (tt / tt[-1]) ** 2
        add(fx, t0s, np.diff(riser, prepend=0) * 0.5, 0.5)
        # 「しなかった」直後: クラッシュでドロップ
        add(fx, t1s, noise_hit(1.6, 0.5, rng), 0.5)
    def nz(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.95 * nz(drums) + 0.55 * nz(bass) + 0.38 * nz(chords) + 0.30 * nz(lead) + 0.45 * nz(fx)
    mix = mix[:int(total * SR)]
    # 最後 0.15 秒だけ短くフェード(ループ再生で頭に繋がるように)
    f = int(0.15 * SR); mix[-f:] *= np.linspace(1, 0, f)
    mix = np.tanh(mix * 1.2)
    return (mix / np.max(np.abs(mix)) * 0.9).astype(np.float32)

if __name__ == '__main__':
    import sys, wave
    x = generate(float(sys.argv[1]) if len(sys.argv) > 1 else 40)
    with wave.open(sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
