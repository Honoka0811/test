# -*- coding: utf-8 -*-
"""和風ローファイBGMをプログラムで合成する(外部音源なし・権利フリー)。
D の陽音階(D E G A B)/ 90BPM。琴風の撥弦メロディ + エレピ風コード + ベース + 軽いビート + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 90
BEAT = 60.0 / BPM
BAR = BEAT * 4

# 4 小節ループのコード(MIDI)。D / Bm / G / A
CHORDS = [[62, 66, 69, 73], [59, 62, 66, 69], [55, 59, 62, 66], [57, 61, 64, 69]]
BASS = [38, 35, 31, 33]
SCALE = [62, 64, 67, 69, 71, 74, 76, 79, 81]  # 陽音階 D E G A B (2 オクターブ弱)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig, gain=1.0):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * gain

def koto(f, dur=1.8):
    """琴風: 倍音ごとに減衰の速さを変え、発音直後にわずかにピッチが上から下りる"""
    n = int(dur * SR); t = np.arange(n) / SR
    bend = 1 + 0.012 * np.exp(-t / 0.03)
    ph = 2 * np.pi * f * np.cumsum(bend) / SR
    sig = np.zeros(n)
    for h, (a, d) in enumerate([(1, .9), (.55, .45), (.35, .25), (.25, .15), (.15, .09), (.1, .06)], 1):
        sig += a * np.sin(h * ph) * np.exp(-t / d)
    sig *= np.minimum(1, t / 0.002)
    return sig.astype(np.float32)

def epiano(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.4))
    env = np.minimum(1, t / 0.01) * np.exp(-t / 1.6) * np.minimum(1, (dur - t) / 0.2).clip(0)
    return (sig * env).astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    env = np.minimum(1, t / 0.008) * np.exp(-t / 0.9) * np.minimum(1, (dur - t) / 0.05).clip(0)
    return (sig * env).astype(np.float32)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)).astype(np.float32)

def noise_hit(rng, dur, decay, smooth):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    if smooth > 1: x = x - np.convolve(x, np.ones(smooth) / smooth, mode='same')  # 低域を削って明るく
    return (x * np.exp(-t / decay)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (3011, 0.6))) / 4
    return (1 - mix) * x + mix * wet

def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same').astype(np.float32)

def make_motif(rng, nbeats=8):
    """2 小節ぶんの旋律(拍位置, 音階インデックス)。順次進行を多めにして歌いやすく"""
    notes = []; idx = rng.integers(2, 6); b = 0.0
    while b < nbeats - 0.5:
        notes.append((b, idx))
        b += rng.choice([0.5, 0.5, 1.0, 1.0, 1.5, 2.0])
        idx = int(np.clip(idx + rng.choice([-2, -1, -1, 1, 1, 2, 0]), 0, len(SCALE) - 1))
    return notes

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR
    mel = np.zeros(n, np.float32); keys = np.zeros(n, np.float32); low = np.zeros(n, np.float32)
    drum = np.zeros(n, np.float32)
    motifs = [make_motif(rng) for _ in range(3)]
    order = [0, 0, 1, 0, 2, 2, 1, 0]  # 2 小節単位の並び(A A B A C C B A)
    nbars = int(np.ceil(total / BAR)) + 1
    k, sn, hat = kick(), None, None
    for b in range(nbars):
        t0 = b * BAR; ci = b % 4
        swing = lambda beat: t0 + beat * BEAT + (0.06 * BEAT if (beat * 2) % 2 == 1 else 0)
        for m in CHORDS[ci]:
            add(keys, t0, epiano(midi(m), BAR + 0.1), 0.22)
        add(low, t0, bass(midi(BASS[ci]), BEAT * 2.5), 0.9)
        add(low, t0 + BEAT * 2.5, bass(midi(BASS[ci]), BEAT * 1.5), 0.6)
        if b >= 2:  # 2 小節のイントロ後にビート
            for beat in (0, 1.5, 2.75):
                add(drum, swing(beat), k, 0.9)
            for beat in (1, 3):
                add(drum, swing(beat), noise_hit(rng, 0.2, 0.05, 6), 0.35)
            for i in range(8):
                add(drum, swing(i / 2), noise_hit(rng, 0.06, 0.012, 2), 0.10 if i % 2 else 0.16)
        if b >= 4 and b % 2 == 0:  # 4 小節目からメロディ
            motif = motifs[order[(b // 2) % len(order)]]
            for beat, idx in motif:
                if rng.random() < 0.9:
                    add(mel, swing(beat), koto(midi(SCALE[idx])), rng.uniform(0.7, 1.0))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    music = 0.5 * norm(reverb(mel, 0.35)) + 0.45 * norm(reverb(keys, 0.3)) + 0.5 * norm(lowpass(low, 8)) + 0.45 * norm(drum)
    music = lowpass(music, 3)  # ローファイ感(高域を少し丸める)
    # テープ風の揺れ(ごく浅い音量のうねり)
    tt = np.arange(len(music)) / SR
    music *= 1 + 0.03 * np.sin(2 * np.pi * 0.5 * tt)
    music = music[:int(total * SR)]
    env = np.ones(len(music), np.float32)
    fi, fo = int(1.0 * SR), int(4.0 * SR)
    env[:fi] = np.linspace(0, 1, fi); env[-fo:] = np.linspace(1, 0, fo)
    music *= env
    return (music / (np.max(np.abs(music)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
