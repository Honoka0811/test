# -*- coding: utf-8 -*-
"""視聴者を引きつけるアップテンポな BGM を numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 124BPM / I-V-vi-IV。4つ打ちキック + クラップ + ハイハット + シンセベース + シンコペしたプラックコード
+ ペンタトニックの軽快なリード + サイドチェイン(ポンピング)。
シーンの開始時刻(markers)に合わせて、イントロ→ドロップ→ブレイク→再ドロップ、と展開する。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys
import numpy as np
from dsp import *

BPM = 124
BEAT = 60.0 / BPM
BAR = BEAT * 4
PROG = [[60, 64, 67], [67, 71, 74], [69, 72, 76], [65, 69, 72]]   # C  G  Am  F
BASS = [48, 43, 45, 41]
# 2小節のリードモチーフ (拍, MIDI, 長さ[拍])  Cペンタ
LEAD = [(0, 76, .5), (.5, 79, .5), (1, 81, 1), (2.5, 79, .5), (3, 76, 1),
        (4, 74, .5), (4.5, 76, .5), (5, 72, 1.5), (6.5, 74, .5), (7, 76, 1)]
PLUCK_PAT = [0, 0.75, 1.5, 2.5, 3.25, 3.5]   # 拍

def kick(rng):
    n = int(0.4 * SR); t = np.arange(n) / SR
    f = 42 + 130 * np.exp(-t / 0.045)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    click = fft_filter(noise(n, rng), lo=2000) * np.exp(-t / 0.004) * 0.6
    return soft_clip((body + click) * 1.6, 1.5).astype(np.float32)

def clap(rng):
    n = int(0.35 * SR); t = np.arange(n) / SR
    env = np.zeros(n, dtype=np.float32)
    for k in range(4):
        env += np.exp(-np.maximum(t - k * 0.011, 0) / (0.015 if k < 3 else 0.11)) * (t >= k * 0.011)
    return (fft_filter(noise(n, rng), lo=900, hi=5500) * env * 0.5).astype(np.float32)

def hat(rng, open_=False):
    n = int((0.28 if open_ else 0.06) * SR); t = np.arange(n) / SR
    return (fft_filter(noise(n, rng), lo=7500) * np.exp(-t / (0.09 if open_ else 0.015)) * 0.22).astype(np.float32)

def crash(rng):
    n = int(1.6 * SR); t = np.arange(n) / SR
    return (fft_filter(noise(n, rng), lo=4000) * np.exp(-t / 0.5) * 0.4).astype(np.float32)

def bass_note(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = saw(f, n, 20) + 0.5 * np.sin(2 * np.pi * f * t)
    bright = fft_filter(x, hi=900); dull = fft_filter(x, hi=220)
    env = np.exp(-t / 0.08)
    return ((bright * env + dull * (1 - env * 0.5)) * env_ar(n, 0.004, 0.02)).astype(np.float32)

def pluck_chord(notes, dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum(saw(midi(m) * d, n, 16) for m in notes for d in (0.997, 1.003)) / (2 * len(notes))
    bright = fft_filter(x, hi=5000); dull = fft_filter(x, hi=700)
    e1 = np.exp(-t / 0.06); e2 = np.exp(-t / 0.25)
    return ((bright * e1 + dull * e2 * 0.8) * env_ar(n, 0.002, 0.03)).astype(np.float32)

def lead_note(f, dur):
    n = int((dur + 0.08) * SR); t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / 0.15, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    x = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) / 1.75   # 丸めの角波風
    env = env_ar(n, 0.01, 0.08)
    return (x * env * 0.55).astype(np.float32)

def pad_chord(notes, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum(saw(midi(m - 12) * d, n, 10) for m in notes for d in (0.994, 1.006)) / (2 * len(notes))
    return (fft_filter(x, hi=1500) * env_ar(n, 0.4, 0.5)).astype(np.float32)

def riser(dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    x = noise(n, rng) * (t / dur) ** 2
    X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    x = np.fft.irfft(X / np.sqrt(1 + (f / 4000) ** 2), n=n)
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1200 * (t / dur) ** 2) / SR) * (t / dur) ** 3 * 0.3
    return ((x * 0.35 + tone) * env_ar(n, 0.05, 0.01)).astype(np.float32)

def sparkle_arp(start_bar_t, chord, bars, rng, buf):
    for b in range(bars):
        for k in range(16):
            if rng.random() < 0.55:
                m = chord[b % 4][rng.integers(0, 3)] + 24
                n = int(0.5 * SR); t = np.arange(n) / SR
                x = np.sin(2 * np.pi * midi(m) * t) * np.exp(-t / 0.12) * 0.25
                add(buf, start_bar_t + b * BAR + k * BEAT / 4, x.astype(np.float32))

def generate(total, markers=None, seed=3):
    """total 秒の BGM。markers = {'drop': 秒, 'break': 秒, 'drop2': 秒} でセクション切り替え(小節頭に量子化)。"""
    markers = markers or {}
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR
    nbars = int(np.ceil(total / BAR)) + 1
    def bar_of(sec): return int(round(sec / BAR))
    drop_bar = bar_of(markers.get('drop', 2 * BAR))
    break_bar = bar_of(markers.get('break', total)) if 'break' in markers else 10 ** 9
    drop2_bar = bar_of(markers.get('drop2', total)) if 'drop2' in markers else 10 ** 9
    end_bar = int(total / BAR)

    drums = np.zeros(n, np.float32); bass = np.zeros(n, np.float32)
    pluck = np.zeros(n, np.float32); lead = np.zeros(n, np.float32)
    pad = np.zeros(n, np.float32); fx = np.zeros(n, np.float32)
    K, C, H, HO = kick(rng), clap(rng), hat(rng), hat(rng, True)
    kick_times = []

    for b in range(nbars):
        t0 = b * BAR
        if t0 > total: break
        ci = b % 4; chord = PROG[ci]
        section = 'intro' if b < drop_bar else ('break' if break_bar <= b < drop2_bar else 'drop')
        # ---- ドラム ----
        if section == 'intro':
            for k in range(8): add(drums, t0 + k * BEAT / 2, H, 0.6 if k % 2 else 0.9)
            if b == drop_bar - 1:                       # ドロップ直前: スネアロール
                for k in range(16): add(drums, t0 + k * BEAT / 4, C, 0.3 + 0.7 * k / 15)
        elif section == 'drop':
            for k in range(4): add(drums, t0 + k * BEAT, K); kick_times.append(t0 + k * BEAT)
            add(drums, t0 + BEAT, C); add(drums, t0 + 3 * BEAT, C)
            for k in range(8): add(drums, t0 + k * BEAT / 2, HO if k == 3 or k == 7 else H, 0.55 if k % 2 else 0.9)
            if b % 4 == 3: add(drums, t0 + 3.5 * BEAT, C, 0.7)      # フィル
            if b == drop_bar or b == drop2_bar: add(drums, t0, crash(rng))
        else:   # break: キックは 1 拍目だけ、ハットは軽く
            add(drums, t0, K, 0.8); kick_times.append(t0)
            for k in range(8): add(drums, t0 + k * BEAT / 2, H, 0.3)
        # ---- ベース ----
        if section == 'drop':
            root = BASS[ci]
            for k in range(8):
                m = root + (12 if k in (3, 7) else 0)
                add(bass, t0 + k * BEAT / 2, bass_note(midi(m), BEAT / 2 * 0.9), 0.9 if k % 2 == 0 else 0.7)
        elif section == 'break':
            add(bass, t0, bass_note(midi(BASS[ci]), BAR * 0.95), 0.7)
        # ---- プラックコード ----
        if section != 'break':
            for beat in PLUCK_PAT:
                add(pluck, t0 + beat * BEAT, pluck_chord(chord), 1.0 if section == 'drop' else 0.55)
        # ---- パッド(イントロ/ブレイクで厚みを出す) ----
        if section in ('intro', 'break'):
            add(pad, t0, pad_chord(chord, BAR + 0.5), 0.5)
        # ---- リード(ドロップの 2 小節目以降、2 小節モチーフ) ----
        if section == 'drop' and (b - drop_bar) % 2 == 0 and b >= drop_bar + 2:
            for beat, m, ln in LEAD:
                add(lead, t0 + beat * BEAT, lead_note(midi(m), ln * BEAT * 0.9))
        # ---- 効果 ----
        if b == drop_bar - 2: add(fx, t0, riser(2 * BAR, rng))
        if b == drop2_bar - 1: add(fx, t0, riser(BAR, rng))
    if 'break' in markers and drop2_bar < 10 ** 9:
        sparkle_arp(break_bar * BAR, PROG, drop2_bar - break_bar, rng, fx)
    # ---- サイドチェイン(キックで沈む) ----
    sc = np.ones(n, np.float32)
    dip = np.concatenate([np.full(int(0.02 * SR), 0.35), np.linspace(0.35, 1.0, int(0.28 * SR))]).astype(np.float32)
    for kt in kick_times:
        s = int(kt * SR); e = min(s + len(dip), n); sc[s:e] = np.minimum(sc[s:e], dip[:e - s])
    lead = delay_fx(lead, BEAT * 0.75, 0.3, 0.25)
    pluck = reverb(pluck, 0.12)
    pad = reverb(pad, 0.3)
    mix = (drums * 0.95 + bass * 0.75 * sc + pluck * 0.55 * sc + lead * 0.5 + pad * 0.5 * sc + fx * 0.6)
    mix = fft_filter(mix, lo=30)
    mix = soft_clip(mix * 1.1, 1.3)
    mix = mix[:int(total * SR)]
    mix *= env_ar(len(mix), 0.02, 1.2)
    return norm(mix, 0.9)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total, {'drop': 5.0, 'break': 29.4, 'drop2': 34.4})
    write_wav(out, x); print('wrote', out, f'{len(x) / SR:.1f}s')
