# -*- coding: utf-8 -*-
"""BGM と効果音(SFX)を timeline.json に合わせてプログラム合成する(外部音源不要・権利フリー)。
Aマイナー / 96BPM。構成:
  hook   : 心拍 + サブドローン + ライザー → 「たった一つ」でインパクト
  pain   : 雨のノイズ床 + まばらなピアノ + 暗いパッド、「裏切られる」で雷鳴
  bamboo : パッドのクレッシェンド + ハイハット + スネアロール + ライザー → 発芽でドロップ(ビート開始)
  reject : ビート継続、12 連のスタンプ音、「あの物語は」でシマー
  core   : フル編成(キック/クラップ/ベース/ピアノ/ストリングス風)、「根を張る時間」でクラッシュ
  close  : ドラム抜き、温かいパッド + ピアノ
  cta    : 軽いプラック + パッド、フェードアウト
使い方: python3 bgm.py [timeline.json] [bgm.wav] [sfx.wav]
"""
import sys, os, json, wave
import numpy as np
from scipy.signal import butter, lfilter

SR = 48000
BPM = 96
BEAT = 60.0 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.abspath(__file__))

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def lp(x, fc, order=2): b, a = butter(order, fc / (SR / 2), 'low'); return lfilter(b, a, x).astype(np.float32)
def hp(x, fc, order=2): b, a = butter(order, fc / (SR / 2), 'high'); return lfilter(b, a, x).astype(np.float32)
def bp(x, lo, hi): return hp(lp(x, hi), lo)
def env_adsr(n, a, d, s, r):
    t = np.arange(n) / SR; T = n / SR
    e = np.ones(n, dtype=np.float32)
    e = np.where(t < a, t / max(a, 1e-4), e)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / max(d, 1e-4), e)
    e = np.where((t >= a + d) & (t < T - r), s, e)
    e = np.where(t >= T - r, s * (T - t) / max(r, 1e-4), e)
    return np.clip(e, 0, 1).astype(np.float32)
def add(buf, start, sig, g=1.0):
    s = int(start * SR); e = min(s + len(sig), len(buf))
    if e > s and s >= 0: buf[s:e] += sig[:e - s] * g

# ---------- 楽器 ----------
def piano(f, dur=1.6, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for h, amp, dec in ((1, 1.0, 0.9), (2, 0.5, 0.6), (3, 0.25, 0.4), (4, 0.12, 0.3), (5, 0.06, 0.25), (6, 0.04, 0.2)):
        sig += amp * np.sin(2 * np.pi * f * h * t * (1 + 0.0004 * h)) * np.exp(-t / dec)
    sig *= np.minimum(1, t / 0.004)
    return (sig * vel * 0.25).astype(np.float32)
def pad(f, dur, a=0.8, r=0.8, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.006, 0, 0.006):
        for h in range(1, 10):
            sig += (1 / h ** 1.3) * np.sin(2 * np.pi * f * h * (1 + det) * t + det * 50)
    sig = lp(sig, 900 * bright + f * 2)
    return (sig * env_adsr(n, a, 0.1, 1.0, r) * 0.08).astype(np.float32)
def strings(f, dur, a=1.2, r=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t)
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.004, 0.004):
        for h in range(1, 14):
            sig += (1 / h) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t)
    sig = lp(sig, 2500)
    return (sig * env_adsr(n, a, 0.2, 1.0, r) * 0.05).astype(np.float32)
def sub(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return (sig * env_adsr(n, 0.01, 0.1, 0.8, 0.08) * 0.5).astype(np.float32)
def bass_pluck(f, dur=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    saw = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 9))
    return (lp(saw, 400 + 1200 * np.exp(-t / 0.1).mean()) * np.exp(-t / 0.18) * 0.5).astype(np.float32)
def kick(dur=0.4, f0=160, f1=45, soft=False):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.045)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / (0.16 if not soft else 0.22))
    click = 0 if soft else 0.3 * np.random.default_rng(1).standard_normal(n) * np.exp(-t / 0.006)
    return ((body + click) * 0.9).astype(np.float32)
def clap(rng):
    n = int(0.25 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    env = sum(np.exp(-np.maximum(t - d, 0) / 0.03) * (t >= d) for d in (0, 0.012, 0.024)) + np.exp(-t / 0.12) * (t >= 0.03)
    return (bp(noise * env, 900, 5000) * 0.55).astype(np.float32)
def hat(rng, dur=0.06, open_=False):
    n = int((0.3 if open_ else dur) * SR); t = np.arange(n) / SR
    return (hp(rng.standard_normal(n).astype(np.float32), 7000) * np.exp(-t / (0.09 if open_ else 0.018)) * 0.22).astype(np.float32)
def snare(rng, vel=1.0):
    n = int(0.2 * SR); t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.06)
    noise = bp(rng.standard_normal(n).astype(np.float32), 1200, 8000) * np.exp(-t / 0.08)
    return ((0.5 * tone + noise) * 0.5 * vel).astype(np.float32)
def riser(rng, dur):
    n = int(dur * SR); t = np.arange(n) / SR; p = t / dur
    noise = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, dtype=np.float32)
    # 区間ごとにカットオフを上げる(簡易スイープ)
    k = 12
    for i in range(k):
        s, e = int(i * n / k), int((i + 1) * n / k)
        out[s:e] = lp(noise, 300 + 9000 * (i / k) ** 2)[s:e]
    sweep = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (2.5 * p)) / SR) * 0.4
    return ((out * 0.6 + sweep) * (p ** 2) * 0.6).astype(np.float32)
def impact(rng, dur=2.5, big=True):
    n = int(dur * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (38 + 60 * np.exp(-t / 0.08)) * t) * np.exp(-t / 0.6)
    noise = lp(rng.standard_normal(n).astype(np.float32), 1800) * np.exp(-t / 0.25)
    tail = lp(rng.standard_normal(n).astype(np.float32), 600) * np.exp(-t / 1.2) * 0.25
    return ((boom * 1.2 + noise * 0.5 + tail) * (1.0 if big else 0.6)).astype(np.float32)
def whoosh(rng, dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (bp(rng.standard_normal(n).astype(np.float32), 400, 6000) * env * 0.5).astype(np.float32)
def crash(rng, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    return (hp(rng.standard_normal(n).astype(np.float32), 4000) * np.exp(-t / 0.7) * 0.35).astype(np.float32)
def shimmer(dur=3.0, notes=(93, 96, 100, 105)):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for i, m in enumerate(notes):
        d = i * 0.08
        sig += np.sin(2 * np.pi * midi(m) * t) * np.exp(-np.maximum(t - d, 0) / 1.4) * (t >= d)
    return (sig * 0.12).astype(np.float32)
def stamp(rng):
    n = int(0.35 * SR); t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (70 + 80 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.08)
    click = bp(rng.standard_normal(n).astype(np.float32), 1500, 6000) * np.exp(-t / 0.01)
    return ((thud * 0.9 + click * 0.5) * 0.8).astype(np.float32)
def heartbeat(rng):
    n = int(0.6 * SR); t = np.arange(n) / SR
    a = np.sin(2 * np.pi * (60 + 40 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.12)
    t2 = np.maximum(t - 0.19, 0)
    b = np.sin(2 * np.pi * (52 + 30 * np.exp(-t2 / 0.05)) * t2) * np.exp(-t2 / 0.1) * (t >= 0.19) * 0.7
    return ((a + b) * 0.8).astype(np.float32)
def key_click(rng):
    n = int(0.05 * SR); t = np.arange(n) / SR
    return (bp(rng.standard_normal(n).astype(np.float32), 2000, 8000) * np.exp(-t / 0.006) * 0.4).astype(np.float32)
def chime(dur=2.0):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * midi(88) * t) + 0.5 * np.sin(2 * np.pi * midi(95) * t)) * np.exp(-t / 0.8) * 0.15).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y
def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.72), (1877, 0.70), (2251, 0.68), (3001, 0.6))) / 4
    return ((1 - mix) * x + mix * lp(wet, 5000)).astype(np.float32)

# ---------- コード(Aマイナー) ----------
CHORDS = {'Am': [57, 60, 64], 'F': [53, 57, 60], 'C': [48, 52, 55, 60], 'G': [55, 59, 62], 'E': [52, 56, 59], 'Dm': [50, 53, 57]}
ROOT = {'Am': 45, 'F': 41, 'C': 48, 'G': 43, 'E': 40, 'Dm': 38}
PROG_DRIVE = ['Am', 'F', 'C', 'G']
PROG_PAIN = ['Am', 'Am', 'F', 'E']
PROG_CLOSE = ['F', 'C', 'G', 'Am']
# メロディ(4 小節、(拍位置, MIDI) )
MELODY = [(0, 69), (1, 72), (2, 76), (3, 74), (4, 72), (5, 71), (6, 69), (8, 67), (9, 69), (10, 72), (11, 71), (12, 69), (13.5, 67), (14.5, 69)]

def generate(tl, seed=11):
    rng = np.random.default_rng(seed)
    total = tl['total']; n = int(total * SR)
    S = {s['id']: s for s in tl['scenes']}
    T = lambda sid, li, pi: S[sid]['lines'][li]['parts'][pi]['start']
    t_one = T('hook', 1, 1)                      # たった一つ
    t_thunder = T('pain', 1, 1)                  # 裏切られる
    t_drop = T('bamboo', 2, 2) - 0.15            # 発芽
    t_stamp0, t_stamp_end = T('reject', 0, 1), S['reject']['lines'][0]['end'] + 0.1
    t_gold = T('reject', 1, 2)                   # あの物語は
    t_core, t_root = S['core']['start'], T('core', 3, 2)   # 根を張る時間
    t_one2 = T('core', 2, 2)
    t_close, t_cta = S['close']['start'], S['cta']['start']
    t_type = T('cta', 0, 3)
    pain0 = S['pain']['start']

    music = {k: np.zeros(n, dtype=np.float32) for k in ('pad', 'piano', 'drums', 'bass', 'strings', 'fx')}
    sfx = np.zeros(n, dtype=np.float32)

    # --- hook: 心拍 + サブドローン + ライザー ---
    tt = np.arange(int((pain0 + 0.5) * SR)) / SR
    drone = np.sin(2 * np.pi * midi(33) * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * tt)) * np.minimum(1, tt / 0.3)
    add(music['bass'], 0, (drone * 0.35 * env_adsr(len(tt), 0.05, 0, 1, 0.5)).astype(np.float32))
    hb = 0.0
    while hb < t_one - 0.3:
        add(music['drums'], hb, heartbeat(rng), 0.9); hb += 1.0
    add(music['fx'], t_one - 1.0, riser(rng, 1.0), 0.8)
    add(sfx, t_one, impact(rng), 1.0)
    add(sfx, 0.0, impact(rng, 1.6, big=False), 0.9)
    add(music['pad'], 0.3, pad(midi(45), pain0 - 0.3, a=1.5, r=0.6, bright=0.4), 0.8)

    # --- pain: 雨 + ピアノ + 暗いパッド ---
    rain_n = int((t_drop - pain0 + 1.0) * SR)
    rt = np.arange(rain_n) / SR
    rain = lp(rng.standard_normal(rain_n).astype(np.float32), 2500) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.17 * rt))
    rain *= env_adsr(rain_n, 1.0, 0, 1, 2.5) * 0.05
    add(music['fx'], pain0, rain)
    bars = int(np.ceil((t_drop - pain0) / BAR)) + 1
    for b in range(bars):
        t0 = pain0 + b * BAR; ch = PROG_PAIN[b % 4]
        for i, m in enumerate(CHORDS[ch]):
            add(music['pad'], t0, pad(midi(m), BAR + 0.6, a=0.6, r=0.6, bright=0.5), 0.9)
        # ピアノ: 拍ごとにアルペジオ(後半は 8 分で密度アップ)
        notes = CHORDS[ch] + [CHORDS[ch][0] + 12]
        step = BEAT if t0 < S['bamboo']['start'] else BEAT / 2
        k = 0; tq = t0
        while tq < t0 + BAR:
            if rng.random() < (0.6 if step == BEAT else 0.85):
                add(music['piano'], tq, piano(midi(notes[k % len(notes)] + 12), 1.4, 0.55 + 0.25 * rng.random()))
            k += 1; tq += step
    add(sfx, t_thunder, impact(rng, 3.0, big=False), 0.7)
    add(sfx, t_thunder + 0.05, lp(rng.standard_normal(int(0.4 * SR)).astype(np.float32), 3000) * np.exp(-np.arange(int(0.4 * SR)) / SR / 0.06) * 0.3)

    # --- bamboo ビルド: ストリングスのクレッシェンド + ハット + スネアロール + ライザー ---
    b0 = S['bamboo']['start']
    for i, m in enumerate(CHORDS['Am']):
        sig = strings(midi(m + 12), t_drop - b0, a=t_drop - b0 - 0.3, r=0.2)
        add(music['strings'], b0, sig, 1.2)
    th = b0 + 2.0
    while th < t_drop - 0.05:
        add(music['drums'], th, hat(rng), 0.6 + 0.4 * (th - b0) / (t_drop - b0)); th += BEAT / 2
    roll0 = t_drop - 1.6; tr = roll0; i = 0
    while tr < t_drop - 0.02:
        add(music['drums'], tr, snare(rng, 0.3 + 0.7 * (tr - roll0) / 1.6)); i += 1
        tr += BEAT / 4 if tr < t_drop - 0.6 else BEAT / 8
    add(music['fx'], t_drop - 1.8, riser(rng, 1.8), 1.0)
    add(sfx, t_drop, impact(rng), 1.0)
    add(sfx, t_drop - 0.25, whoosh(rng, 0.6), 0.8)
    add(music['drums'], t_drop, crash(rng), 0.8)

    # --- ドロップ〜core: フルビート ---
    beat_end = t_close - 0.1
    nb = int(np.ceil((beat_end - t_drop) / BAR))
    for b in range(nb):
        t0 = t_drop + b * BAR; ch = PROG_DRIVE[b % 4]
        inten = 1.0 if t0 < t_core else 1.15
        last = t0 + BAR > beat_end - 0.5
        # パッド + ストリングス
        for i, m in enumerate(CHORDS[ch]):
            add(music['pad'], t0, pad(midi(m), BAR + 0.5, a=0.3, r=0.5, bright=1.0), 1.0)
            if t0 >= t_core - 0.01:
                add(music['strings'], t0, strings(midi(m + 12), BAR + 0.4, a=0.4, r=0.4), 0.9)
        # ベース: 8 分
        for k in range(8):
            f = midi(ROOT[ch] - 12)
            add(music['bass'], t0 + k * BEAT / 2, sub(f, BEAT / 2 * 0.9), 0.7 if k % 2 == 0 else 0.5)
            add(music['bass'], t0 + k * BEAT / 2, bass_pluck(midi(ROOT[ch])), 0.35)
        # ドラム
        for beat_pos in (0, 2):
            add(music['drums'], t0 + beat_pos * BEAT, kick(), inten)
        add(music['drums'], t0 + 2.75 * BEAT, kick(), 0.8 * inten)
        for beat_pos in (1, 3):
            add(music['drums'], t0 + beat_pos * BEAT, clap(rng), 0.9 * inten)
            add(music['drums'], t0 + beat_pos * BEAT, snare(rng, 0.5), 0.6)
        for k in range(8):
            add(music['drums'], t0 + k * BEAT / 2, hat(rng, open_=(k == 7)), 0.8 if k % 2 == 0 else 0.5)
        if last:
            for k in range(8):
                add(music['drums'], t0 + 3 * BEAT + k * BEAT / 8, snare(rng, 0.4 + 0.6 * k / 8), 0.8)
        # ピアノ: コードのスタブ(1拍目、3.5拍目) + メロディ
        for pos in (0, 3.5):
            for m in CHORDS[ch]:
                add(music['piano'], t0 + pos * BEAT, piano(midi(m + 12), 1.0, 0.5), 0.8)
        mel_bar = b % 4
        for pos, m in MELODY:
            if int(pos // 4) == mel_bar:
                tq = t0 + (pos % 4) * BEAT
                add(music['piano'], tq, piano(midi(m), 1.2, 0.9), 1.0)
                if t0 >= t_core - 0.01:
                    add(music['piano'], tq, piano(midi(m + 12), 1.2, 0.6), 0.7)
    # スタンプ 12 連
    dt = (t_stamp_end - t_stamp0) / 12
    for i in range(12):
        add(sfx, t_stamp0 + i * dt, stamp(rng), 0.8 + 0.2 * i / 12)
    add(sfx, t_gold - 0.4, whoosh(rng, 0.5), 0.6)
    add(sfx, t_gold, shimmer(3.5), 1.2)
    add(music['fx'], t_gold, impact(rng, 2.0, big=False), 0.4)
    add(sfx, t_one2, impact(rng, 1.5, big=False), 0.7)
    add(music['fx'], t_root - 1.2, riser(rng, 1.2), 0.8)
    add(sfx, t_root, impact(rng), 0.9)
    add(music['drums'], t_root, crash(rng), 1.0)
    add(sfx, t_root, shimmer(3.0, (81, 88, 93, 100)), 0.8)

    # --- close: ドラム抜き、温かいコード ---
    add(music['drums'], t_close, crash(rng, 2.5), 0.5)
    nb = int(np.ceil((t_cta - t_close) / BAR)) + 1
    for b in range(nb):
        t0 = t_close + b * BAR; ch = PROG_CLOSE[b % 4]
        for m in CHORDS[ch]:
            add(music['pad'], t0, pad(midi(m), BAR + 0.8, a=0.5, r=0.8, bright=0.9), 1.0)
            add(music['strings'], t0, strings(midi(m + 12), BAR + 0.6, a=0.8, r=0.6), 0.6)
        notes = CHORDS[ch] + [CHORDS[ch][0] + 12]
        for k in range(8):
            add(music['piano'], t0 + k * BEAT / 2, piano(midi(notes[k % len(notes)] + 12), 1.6, 0.5), 0.8)
    add(sfx, S['close']['lines'][1]['start'], shimmer(2.5, (88, 93, 96, 100)), 0.9)

    # --- cta: 軽いプラック + パッド ---
    nb = int(np.ceil((total - t_cta) / BAR)) + 1
    for b in range(nb):
        t0 = t_cta + b * BAR; ch = PROG_DRIVE[b % 4]
        for m in CHORDS[ch]:
            add(music['pad'], t0, pad(midi(m), BAR + 0.6, a=0.4, r=0.6, bright=0.7), 0.8)
        notes = CHORDS[ch] + [CHORDS[ch][0] + 12]
        for k in range(8):
            if k % 2 == 0 or rng.random() < 0.5:
                add(music['piano'], t0 + k * BEAT / 2, piano(midi(notes[(k * 2) % len(notes)] + 24), 0.8, 0.35), 0.8)
        add(music['drums'], t0, kick(soft=True), 0.5)
        add(music['drums'], t0 + 2 * BEAT, kick(soft=True), 0.4)
    for i in range(4):
        add(sfx, t_type + i * 0.14, key_click(rng), 1.0)
    add(sfx, T('cta', 0, 4), chime(), 1.0)
    add(sfx, S['cta']['lines'][1]['start'], shimmer(2.5, (93, 100, 105)), 0.6)

    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.55 * norm(music['pad']) + 0.6 * norm(reverb(music['piano'], 0.3)) + 0.95 * norm(music['drums'])
           + 0.6 * norm(music['bass']) + 0.45 * norm(music['strings']) + 0.5 * norm(music['fx']))
    mix = reverb(mix, 0.12)
    mix *= env_adsr(n, 0.5, 0, 1, 2.5)
    mix = norm(mix) * 0.9
    sfx = reverb(sfx, 0.2); sfx = norm(sfx) * 0.9
    return mix.astype(np.float32), sfx.astype(np.float32)

def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    tlp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'timeline.json')
    tl = json.load(open(tlp, encoding='utf-8'))
    bgm, sfx = generate(tl)
    write(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'bgm.wav'), bgm)
    write(sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, 'output', 'sfx.wav'), sfx)
    print('wrote bgm/sfx', f"{len(bgm) / SR:.1f}s")
