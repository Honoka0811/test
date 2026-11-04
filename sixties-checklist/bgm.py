# -*- coding: utf-8 -*-
"""パッヘルベル「カノン」(ニ長調・パブリックドメイン)を明るいポップ・クラシック風にアレンジして numpy だけで合成する。
108BPM。ピアノ風メロディ 2 声(カノン=追いかけ)+ ハープ風アルペジオ + 弦パッド + ピチカート低音 + 簡易リバーブ。ステレオ。
外部音源・サンプルを使わないため権利表記は不要。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 108
BEAT = 60.0 / BPM
CYCLE = 16 * BEAT            # 8 和音 × 2 拍 = カノンの 1 周(約 8.9 秒)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

# ---------- 楽譜(MIDI ノート) ----------
BASS = [50, 45, 47, 42, 43, 50, 43, 45]                       # D A B F# G D G A(通奏低音)
CHORDS = [[62, 66, 69], [61, 64, 69], [62, 66, 71], [61, 66, 69],
          [62, 67, 71], [62, 66, 69], [59, 62, 67], [61, 64, 69]]
# 旋律の各バリエーション: 和音ごと(2 拍)の音列。長さ 2=四分音符, 4=八分音符, 8=十六分音符
V1 = [[78, 76], [74, 73], [71, 69], [71, 73], [74, 73], [71, 69], [67, 66], [67, 64]]
V2 = [[74, 73], [71, 69], [67, 66], [67, 64], [67, 69], [71, 73], [74, 71], [73, 69]]
V3 = [[62, 66, 69, 67], [66, 62, 66, 64], [62, 59, 62, 69], [67, 71, 69, 67],
      [66, 62, 64, 73], [74, 78, 81, 69], [71, 67, 69, 66], [62, 74, 74, 73]]
V4 = [[74, 73, 74, 62, 61, 69, 64, 66], [62, 74, 73, 71, 73, 78, 81, 83],
      [79, 78, 76, 79, 78, 76, 74, 73], [71, 69, 67, 66, 64, 67, 66, 64],
      [62, 64, 66, 67, 69, 64, 69, 67], [66, 71, 69, 67, 69, 67, 66, 64],
      [62, 59, 71, 73, 74, 73, 71, 69], [67, 66, 64, 71, 69, 71, 69, 67]]

# 周回ごとの編成: (第1声, 第1声の移調, 第2声, 第2声の移調, ハープ, ピチカート和音, 強さ)
PLAN = [
    (V1, 0, None, 0, True, False, 0.75),
    (V2, 0, None, 0, True, True, 0.85),
    (V3, 0, V1, -12, True, True, 0.95),
    (V4, 0, V2, -12, True, True, 1.0),
    (V1, 0, V3, 0, True, True, 1.0),
    (V4, 0, V2, -12, True, True, 1.0),
    (V3, 0, V1, -12, True, True, 0.95),
    (V1, 0, V3, -12, True, True, 0.9),
]

# ---------- 音色 ----------
def piano(f, dur, vel=1.0):
    """ピアノ風: 倍音加算 + 倍音ごとの減衰 + 離鍵後の短いリリース"""
    ring = min(dur + 1.2, 3.0)
    n = int(ring * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    bright = (f / 440.0) ** 0.35
    for h in range(1, 9):
        if f * h > 16000: break
        amp = 1.0 / h ** 1.25
        dec = np.exp(-t * (1.6 + 0.9 * h) * bright)
        sig += amp * dec * np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * t)
    sig *= np.exp(-t * 0.5)
    rel = np.ones(n, dtype=np.float32)
    k = int(dur * SR)
    if k < n: rel[k:] = np.exp(-(t[k:] - dur) * 9.0)
    att = np.minimum(1.0, t / 0.004)
    hammer = np.random.default_rng(int(f)).standard_normal(n).astype(np.float32) * np.exp(-t / 0.004) * 0.08
    return ((sig * rel * att + hammer) * vel * 0.28).astype(np.float32)

def harp(f, dur, vel=1.0):
    n = int(min(dur + 1.0, 2.2) * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 6)
           + 0.2 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 9)) * np.exp(-t * 2.6)
    return (sig * np.minimum(1.0, t / 0.003) * vel * 0.22).astype(np.float32)

def pizz(f, dur, vel=1.0):
    n = int(0.9 * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 8)
           + 0.15 * np.sin(2 * np.pi * 3 * f * t)) * np.exp(-t * 5.5)
    return (sig * np.minimum(1.0, t / 0.004) * vel * 0.5).astype(np.float32)

def strings(f, dur, vel=1.0, seed=0):
    n = int((dur + 0.5) * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * t + rng.uniform(0, 6.28)) * np.minimum(1, t / 0.6)
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.006, 0.0, 0.006):
        for h in range(1, 8):
            sig += (1.0 / h ** 1.6) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + rng.uniform(0, 6.28))
    env = np.minimum(1.0, t / 0.35) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.25))
    return (sig * env * vel * 0.06).astype(np.float32)

# ---------- ミキシング ----------
def add(buf, start_s, sig, pan=0.0):
    """pan: -1(左)〜+1(右)。等パワー"""
    s = int(start_s * SR); e = min(s + len(sig), buf.shape[1])
    if e <= s: return
    a = (pan + 1) / 2 * np.pi / 2
    buf[0, s:e] += sig[:e - s] * np.cos(a)
    buf[1, s:e] += sig[:e - s] * np.sin(a)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.22):
    taps = ((1553, 0.70), (1877, 0.68), (2251, 0.66), (2963, 0.62))
    wet = sum(comb(x, d, g) for d, g in taps) / len(taps)
    return (1 - mix) * x + mix * wet

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    buf = np.zeros((2, n), dtype=np.float32)
    ncycles = int(np.ceil((total - 2.0) / CYCLE))
    for c in range(ncycles):
        plan = PLAN[c % len(PLAN)]
        v1, tr1, v2, tr2, use_harp, use_pizz, level = plan
        last = (c == ncycles - 1)
        for ch in range(8):
            t0 = c * CYCLE + ch * 2 * BEAT
            if t0 >= total: break
            # 通奏低音(ピチカート)
            add(buf, t0, pizz(midi(BASS[ch]), 2 * BEAT, 0.9 * level), 0.0)
            if use_pizz:
                add(buf, t0 + BEAT, pizz(midi(BASS[ch] + 12), BEAT, 0.35 * level), -0.1)
            # 弦パッド(和音)
            for i, m in enumerate(CHORDS[ch]):
                add(buf, t0, strings(midi(m), 2 * BEAT, 0.9 * level, seed=ch * 10 + i), (i - 1) * 0.5)
            # ハープ風アルペジオ(八分音符で上行)
            if use_harp:
                arp = [CHORDS[ch][0] - 12, CHORDS[ch][0], CHORDS[ch][1], CHORDS[ch][2], CHORDS[ch][0] + 12, CHORDS[ch][2], CHORDS[ch][1], CHORDS[ch][0]]
                for k in range(4):
                    m = arp[k if c % 2 == 0 else k + 4]
                    add(buf, t0 + k * BEAT / 2, harp(midi(m), BEAT / 2, 0.55 * level * rng.uniform(0.85, 1.0)), 0.35 + 0.1 * k)
            # ピチカート和音(2 拍目の裏)
            if use_pizz:
                for i, m in enumerate(CHORDS[ch]):
                    add(buf, t0 + 1.5 * BEAT, pizz(midi(m), BEAT / 2, 0.22 * level), (i - 1) * 0.4)
            # 第 1 声・第 2 声(ピアノ)
            for voice, tr, pan, gain in ((v1, tr1, 0.22, 1.0), (v2, tr2, -0.25, 0.7)):
                if voice is None: continue
                notes = voice[ch]; d = 2 * BEAT / len(notes)
                for k, m in enumerate(notes):
                    vel = gain * level * (1.0 if k % 2 == 0 else 0.8) * rng.uniform(0.9, 1.0)
                    add(buf, t0 + k * d + rng.uniform(0, 0.006), piano(midi(m + tr), d * 0.98, vel), pan)
    # 終止: 最後の周回のあとは D 和音を鳴らして伸ばす
    t_end = ncycles * CYCLE
    if t_end < total:
        add(buf, t_end, pizz(midi(50), 4 * BEAT, 1.0), 0.0)
        add(buf, t_end, pizz(midi(38), 4 * BEAT, 0.6), 0.0)
        for i, m in enumerate([62, 66, 69, 74]):
            add(buf, t_end, strings(midi(m), total - t_end - 0.3, 0.9, seed=100 + i), (i - 1.5) * 0.35)
        for k, m in enumerate([50, 57, 62, 66, 69, 74, 78, 81]):
            add(buf, t_end + k * BEAT / 4, harp(midi(m), 1.5, 0.6), -0.4 + k * 0.1)
        add(buf, t_end + 2 * BEAT, piano(midi(78), 2.0, 0.9), 0.2)
        add(buf, t_end + 2 * BEAT, piano(midi(74), 2.0, 0.6), -0.2)
    out = np.stack([reverb(buf[0]), reverb(buf[1])])
    # フェードイン 1 秒、終わり 3 秒フェードアウト
    env = np.ones(n, dtype=np.float32)
    fi, fo = int(1.0 * SR), int(3.0 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo) ** 1.5
    out *= env
    return (out / (np.max(np.abs(out)) + 1e-9) * 0.9).astype(np.float32)

def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x.T, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 66.6
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    write(out, x)
    print('wrote', out, f'{x.shape[1] / SR:.1f}s')
