# -*- coding: utf-8 -*-
"""「1秒に1円」用BGMをプログラムで合成する(外部音源不要・権利フリー)。
Aマイナー / 120BPM。毎秒ちょうどに鳴る時計のチック音(映像の「1秒=1円」の点滅と同期)
+ パッド + 低音のパルス + アルペジオ + 大きな数字が出る瞬間の低い「ドン」+ 場面転換前のライザー + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 120
BEAT = 60.0 / BPM          # 0.5 秒
BAR = BEAT * 4             # 2 秒

# シーン境界(render.html の SCENES と対応)と、各シーンで「結果」がスタンプされる時刻
SCENE_STARTS = [0, 6.5, 12, 18.5, 25, 32, 40, 49, 58]
RESULT_AT = [s + 1.6 for s in SCENE_STARTS[1:]]
TOTAL_DEFAULT = 67

# コード進行(MIDI)。Am - F - C - G / Am - F - Dm - E を交互に、1コード=1小節(2秒)
PROG = [
    [57, 60, 64, 69], [53, 57, 60, 65], [48, 52, 55, 60], [55, 59, 62, 67],
    [57, 60, 64, 69], [53, 57, 60, 65], [50, 53, 57, 62], [52, 56, 59, 64],
]
ROOTS = [45, 41, 36, 43, 45, 41, 38, 40]
ARP = [[69, 72, 76, 81], [65, 69, 72, 77], [67, 72, 76, 79], [67, 71, 74, 79],
       [69, 72, 76, 81], [65, 69, 72, 77], [62, 65, 69, 74], [64, 68, 71, 76]]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig, gain=1.0):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * gain

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: env[:na] = np.linspace(0, 1, na)
    if nr: env[n - nr:] = np.minimum(env[n - nr:], np.linspace(1, 0, nr))
    return env

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.0015 * np.sin(2 * np.pi * 0.3 * t + rng.uniform(0, 6.28))
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.003, 0.003):
        for h in range(1, 6):
            sig += (1 / h ** 1.6) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + rng.uniform(0, 6.28))
    return sig * env_ar(n, 0.4, 0.6)

def tick(rng):
    """時計のチック: 短いクリック(帯域ノイズ) + 高い木質のブリップ"""
    n = int(0.06 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    noise = np.convolve(noise, np.ones(6) / 6, mode='same') - np.convolve(noise, np.ones(40) / 40, mode='same')
    click = noise * np.exp(-t / 0.004)
    blip = np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.012) + 0.5 * np.sin(2 * np.pi * 3600 * t) * np.exp(-t / 0.006)
    return (click * 0.9 + blip * 0.6).astype(np.float32)

def bass_pulse(f, dur=0.42):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.08)
    return (sig * env_ar(n, 0.004, 0.25) * np.exp(-t / 0.5)).astype(np.float32)

def boom(dur=1.6, rng=None):
    """大きな数字が出る瞬間の低い「ドン」(ピッチが落ちるサブ + 短いノイズ)"""
    n = int(dur * SR); t = np.arange(n) / SR
    f = 38 + 90 * np.exp(-t / 0.06)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t / 0.45)
    noise = rng.standard_normal(n).astype(np.float32) * np.exp(-t / 0.03)
    noise = np.convolve(noise, np.ones(24) / 24, mode='same')
    return (body + 0.3 * noise).astype(np.float32)

def pluck(f, dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 3 * f * t)) * np.exp(-t / 0.13)).astype(np.float32)

def riser(dur, rng):
    """場面転換前の上昇ノイズ(フィルタ開き + 上がるピッチ)"""
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    k = (1 + 60 * (1 - t / dur)).astype(int)  # だんだん明るく
    out = np.zeros(n, dtype=np.float32)
    step = SR // 20
    for s in range(0, n, step):
        kk = max(1, int(k[s]))
        out[s:s + step] = np.convolve(noise[s:s + step], np.ones(kk) / kk, mode='same')
    f = 110 * 2 ** (t / dur * 2)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4
    env = (t / dur) ** 2.2
    return ((out * 0.9 + tone) * env).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1427, 0.70), (1801, 0.68), (2131, 0.66), (9601, 0.40))) / 4
    return (1 - mix) * x + mix * wet

def intensity(t):
    """シーンが進むほど厚くなる(0..1)"""
    return float(np.interp(t, [0, 6.5, 12, 18.5, 25, 32, 40, 49, 58, 60, 67], [0.15, 0.25, 0.35, 0.45, 0.55, 0.75, 0.9, 1.0, 0.6, 0.6, 0.7]))

def generate(total=TOTAL_DEFAULT, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pad = np.zeros(n, dtype=np.float32); bass = np.zeros(n, dtype=np.float32)
    arp = np.zeros(n, dtype=np.float32); perc = np.zeros(n, dtype=np.float32)
    fx = np.zeros(n, dtype=np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR
        chord = PROG[b % len(PROG)]; root = ROOTS[b % len(ROOTS)]
        inten = intensity(t0)
        for note in chord:
            add(pad, t0, pad_note(midi(note), BAR + 0.6, rng), 0.11 * (0.6 + 0.4 * inten))
        # 低音: 1拍目と3拍目(2秒に2回)、終盤はオクターブ上も
        for beat in (0, 2):
            if t0 >= 12:
                add(bass, t0 + beat * BEAT, bass_pulse(midi(root)), 0.5 * inten)
            if t0 >= 32:
                add(bass, t0 + beat * BEAT + BEAT / 2, bass_pulse(midi(root + 12), 0.25), 0.22 * inten)
        # アルペジオ: 16分音符で、強度に応じて音数が増える
        if t0 >= 18.5:
            notes = ARP[b % len(ARP)]
            for k in range(16):
                if rng.random() < 0.35 + 0.5 * inten:
                    add(arp, t0 + k * BEAT / 4, pluck(midi(notes[k % 4] + (12 if k % 8 == 7 else 0))), 0.16 * inten)
    # 時計のチック(毎秒ちょうど)。導入は目立たせ、以後は控えめに
    for s in range(int(total)):
        g = 0.9 if s < 6.5 else 0.45
        add(perc, s, tick(rng), g)
    # 結果スタンプの「ドン」
    for r in RESULT_AT:
        if r < total:
            big = r >= 32
            add(fx, r - 0.02, boom(rng=rng), 0.95 if big else 0.6)
    # 場面転換前のライザー(大きな桁のシーンへ)
    for s in (25, 32, 40, 49):
        add(fx, s - 1.6, riser(1.6, rng), 0.35)
    mix = reverb(pad, 0.35) + bass + reverb(arp, 0.3) + perc + fx
    # 最後の 1.2 秒はフェードアウト
    fo = int(1.2 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix = mix / max(1e-6, np.max(np.abs(mix))) * 0.9
    return mix.astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else TOTAL_DEFAULT
    out = sys.argv[2] if len(sys.argv) > 2 else 'output/bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{total}s')
