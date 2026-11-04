# -*- coding: utf-8 -*-
"""BGM と効果音をプログラムで合成する(外部音源なし・権利フリー)。
BGM: Aマイナー / 112BPM のシネマティック・ポップ(Am–F–C–G)。シーンに合わせて編成が変わる。
  冒頭: ライザー → インパクト → パッド+アルペジオ / 概要: ビート控えめ / ランキング: フルビート(順位が上がるほど厚く)
  1位: ドラムロールで溜めてドロップ / 番外編: ハーフタイム / 鉄道: 汽車のリズム / あじあ号: フル / 結び: パッドのみ
効果音: ウーッシュ、インパクト、ドラムロール、スタンプ、汽笛。タイミングは render.html と同じ値を使う。
単体実行: python3 music.py  → output/bgm.wav, output/sfx.wav
"""
import os, json, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 112
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.abspath(__file__))
R1_REVEAL = 1.5     # render.html と同じ
BONUS_STAMP = 4.3

PROG = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
ROOTS = [45, 41, 48, 43]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tvec(dur): return np.arange(int(dur * SR)) / SR
def lp(x, f, order=2): return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)

def add(buf, t0, sig, g=1.0):
    s = int(t0 * SR)
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += g * sig[:e - s]

def load_timing():
    with open(os.path.join(HERE, 'timing.js'), encoding='utf-8') as f:
        src = f.read()
    return json.loads(src[src.index('{'): src.rindex('}') + 1])

# ---------- 音源 ----------
RNG = np.random.default_rng(11)
def noise(dur): return RNG.standard_normal(int(dur * SR))

def kick(dur=0.35, f0=150, f1=45):
    t = tvec(dur); f = f1 + (f0 - f1) * np.exp(-t / 0.045)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)

def clap():
    t = tvec(0.25); n = bp(noise(0.25), 900, 5000)
    env = np.exp(-t / 0.07) * (1 + 0.6 * (np.sin(2 * np.pi * 90 * t) > 0) * (t < 0.03))
    return 0.6 * n * env + 0.25 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)

def hat(dur=0.05, open_=False):
    t = tvec(0.3 if open_ else dur); n = hp(noise(len(t) / SR), 7000)
    return n * np.exp(-t / (0.12 if open_ else 0.018))

def snare():
    t = tvec(0.18); return 0.7 * bp(noise(0.18), 1500, 7000) * np.exp(-t / 0.06) + 0.3 * np.sin(2 * np.pi * 200 * t) * np.exp(-t / 0.04)

def saw(f, dur, nh=12):
    t = tvec(dur); x = np.zeros_like(t)
    for h in range(1, nh + 1): x += np.sin(2 * np.pi * f * h * t) / h
    return x

def bass_note(f, dur):
    t = tvec(dur); x = lp(saw(f, dur, 8), 600)
    env = np.minimum(1, t / 0.005) * np.exp(-t / (dur * 0.9))
    return x * env

def pad_chord(chord, dur):
    t = tvec(dur); x = np.zeros_like(t)
    for m in chord:
        for det in (-0.006, 0.0, 0.006):
            x += saw(midi(m) * (1 + det), dur, 6) * 0.33
    x = lp(x, 1800)
    a = min(0.6, dur / 3); env = np.minimum(1, t / a) * np.minimum(1, (dur - t) / 0.4)
    return x * env

def pluck(f, dur=0.35):
    t = tvec(dur); x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t)
    return x * np.exp(-t / 0.12)

def stab(chord, dur=0.9):
    t = tvec(dur); x = sum(saw(midi(m + 12), dur, 10) for m in chord) + sum(saw(midi(m), dur, 10) for m in chord)
    return lp(x, 3500) * np.exp(-t / 0.35)

# ---------- 効果音 ----------
def whoosh(dur=0.55, rise=True):
    t = tvec(dur); n = noise(dur); out = np.zeros_like(n); seg = 512
    for i in range(0, len(n), seg):
        p = i / len(n); fc = (300 + 5000 * p) if rise else (5300 - 5000 * p)
        out[i:i + seg] = bp(n[max(0, i - 2048): i + seg], fc * 0.6, min(fc * 1.6, 20000))[-len(n[i:i + seg]):]
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return out * env

def riser(dur):
    t = tvec(dur); n = noise(dur); out = np.zeros_like(n); seg = 1024
    for i in range(0, len(n), seg):
        p = i / len(n); fc = 200 * (40 ** p)
        out[i:i + seg] = bp(n[max(0, i - 4096): i + seg], fc * 0.7, min(fc * 1.4, 20000))[-len(n[i:i + seg]):]
    tone = np.sin(2 * np.pi * np.cumsum(110 * (4 ** (t / dur))) / SR) * 0.3
    return (out + tone) * (t / dur) ** 2

def impact(big=False):
    dur = 2.2 if big else 1.2; t = tvec(dur)
    boom = kick(dur, 120, 32) * (1.4 if big else 1.0)
    crack = lp(noise(dur), 6000) * np.exp(-t / (0.09 if big else 0.05))
    tail = lp(noise(dur), 400) * np.exp(-t / (0.8 if big else 0.4)) * 0.5
    return boom + 0.5 * crack + tail

def drumroll(dur):
    out = np.zeros(int(dur * SR) + SR // 2); t = 0.0
    while t < dur:
        p = t / dur; add(out, t, snare(), 0.25 + 0.75 * p ** 1.5)
        t += lerp(0.11, 0.035, p)
    return out

def lerp(a, b, p): return a + (b - a) * p

def whistle(dur=1.1):
    t = tvec(dur); env = np.minimum(1, t / 0.06) * np.minimum(1, (dur - t) / 0.25)
    x = sum(np.sin(2 * np.pi * f * t * (1 + 0.004 * np.sin(2 * np.pi * 5 * t))) for f in (midi(81), midi(84), midi(88)))
    return (x + 0.3 * bp(noise(dur), 1500, 4000)) * env * 0.4

def tick():
    t = tvec(0.04); return np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.008)

# ---------- 構成 ----------
def generate(timing):
    S = {s['id']: s for s in timing['scenes']}
    total = timing['total']
    n = int(total * SR) + SR
    drums, bass, pads, arps, stabs, sfx = (np.zeros(n) for _ in range(6))
    kenv = np.zeros(n)  # サイドチェイン用

    def scene_at(t):
        for s in timing['scenes']:
            if s['s'] <= t < s['s'] + s['d']: return s['id'], t - s['s']
        return 'end', t - S['end']['s']

    hook_impact = 1.65
    nbars = int(np.ceil(total / BAR)) + 1
    for b in range(nbars):
        bar_t = b * BAR
        ci = b % 4; chord = PROG[ci]; root = ROOTS[ci]
        sid0, _ = scene_at(bar_t)
        # パッド(冒頭のインパクト前と 1位の溜めは無し)
        if bar_t + BAR > hook_impact:
            sig = pad_chord(chord, BAR + 0.3)
            g = 0.5 if sid0 in ('end', 'bonus', 'hook', 'overview') else 0.35
            add(pads, max(bar_t, hook_impact), sig[int(max(0, hook_impact - bar_t) * SR):], g)
        for step in range(16):   # 16分音符
            t = bar_t + step * BEAT / 4
            if t >= total: break
            sid, lt = scene_at(t)
            if t < hook_impact: continue
            if sid == 'r1' and lt < R1_REVEAL: continue        # 1位の溜め: 無音にしてドラムロールを聞かせる
            if sid == 'end' and lt > 0: full = False
            rank_lvl = {'r5': 0, 'r4': 1, 'r3': 2, 'r2': 3, 'r1': 4}.get(sid)
            beat_kick = step % 4 == 0
            if sid == 'hook':
                if step == 0: add(drums, t, kick(), 0.8); add(kenv, t, np.exp(-tvec(0.3) / 0.12))
                if step % 2 == 0: add(arps, t, pluck(midi(chord[(step // 2) % 3] + 12)), 0.5)
            elif sid == 'overview':
                if beat_kick: add(drums, t, kick(), 0.8); add(kenv, t, np.exp(-tvec(0.3) / 0.12))
                if step % 4 == 2: add(drums, t, hat(), 0.25)
                if step % 2 == 0: add(bass, t, bass_note(midi(root - 12), BEAT / 2 * 0.9), 0.7)
                if step % 2 == 0: add(arps, t, pluck(midi(chord[(step // 2) % 3] + 12)), 0.45)
            elif rank_lvl is not None or sid in ('asia', 'rail'):
                lvl = rank_lvl if rank_lvl is not None else 3
                if beat_kick: add(drums, t, kick(), 1.0); add(kenv, t, np.exp(-tvec(0.3) / 0.12))
                if step in (4, 12): add(drums, t, clap(), 0.55 + 0.08 * lvl)
                if sid == 'rail':
                    # 汽車のリズム: 16分のハットにアクセント
                    add(drums, t, hat(), 0.45 if step % 4 in (0, 3) else 0.18)
                else:
                    add(drums, t, hat(), (0.3 if step % 2 == 0 else 0.15) * (0.6 + 0.12 * lvl))
                    if lvl >= 2 and step % 8 == 6: add(drums, t, hat(open_=True), 0.15)
                add(bass, t, bass_note(midi(root - 12 + (12 if step % 4 == 2 else 0)), BEAT / 4 * 0.95), 0.6)
                pat = [0, 1, 2, 1, 2, 0, 1, 2]
                add(arps, t, pluck(midi(chord[pat[step % 8]] + 12 + (12 if (lvl >= 3 and step % 8 == 7) else 0))), 0.38 + 0.04 * lvl)
                if sid == 'r1' and step == 0: add(stabs, t, stab(chord, 1.2), 0.25)
            elif sid == 'bonus':
                if step == 0: add(drums, t, kick(), 0.9); add(kenv, t, np.exp(-tvec(0.3) / 0.12))
                if step == 8: add(drums, t, clap(), 0.5)
                if step % 4 == 0: add(drums, t, hat(), 0.2)
                if step % 4 == 0: add(bass, t, bass_note(midi(root - 12), BEAT * 0.9), 0.6)
                if step % 3 == 0: add(arps, t, pluck(midi(chord[(step // 3) % 3] + 24)), 0.3)
            elif sid == 'end':
                if step % 4 == 0 and lt < 4.2: add(arps, t, pluck(midi(chord[(step // 4) % 3] + 12), 0.8), 0.35)
                if step == 0 and lt > 4.2: add(arps, t, pluck(midi(chord[0] + 12), 1.2), 0.3)

    # サイドチェイン(キックに合わせてパッド・ベースを沈める)
    duck = 1 - 0.55 * np.clip(kenv, 0, 1)
    music = 0.55 * drums + 0.55 * bass * duck + 0.30 * pads * duck + 0.30 * arps + stabs
    # 1位の溜めの間は全体を絞り、ドロップで戻す
    r1 = S['r1']['s']
    tt = np.arange(n) / SR
    gate = np.ones(n)
    m = (tt >= r1) & (tt < r1 + R1_REVEAL)
    gate[m] = 0.15
    music *= lp(gate, 30, 1)
    # 冒頭フェードイン・終わりのフェードアウト
    music *= np.clip(tt / 0.3, 0, 1) * np.clip((total - tt) / 3.0, 0, 1)

    # ---------- 効果音 ----------
    add(sfx, 0.05, riser(1.6), 0.5)
    add(sfx, 0.35, impact(), 0.45); add(sfx, 0.8, impact(), 0.5); add(sfx, hook_impact, impact(True), 0.9)
    for sid in ('overview', 'r5', 'r4', 'r3', 'r2', 'r1', 'bonus', 'rail', 'asia', 'end'):
        add(sfx, S[sid]['s'] - 0.35, whoosh(0.5), 0.35)
    for sid in ('r5', 'r4', 'r3', 'r2'):
        add(sfx, S[sid]['s'] + 0.35, impact(), 0.75)
    add(sfx, r1 + 0.05, drumroll(R1_REVEAL - 0.1), 0.55)
    add(sfx, r1 + R1_REVEAL, impact(True), 1.0)
    add(sfx, S['bonus']['s'] + 0.35, impact(), 0.6)
    add(sfx, S['bonus']['s'] + BONUS_STAMP, impact(), 0.8)
    add(sfx, S['end']['s'] + 4.2, impact(True), 0.6)
    for k, g in ((2.3, 0.25), (5.2, 0.25), (9.0, 0.25)):
        add(sfx, S['rail']['s'] + k, whoosh(0.7), g)
    add(sfx, S['asia']['s'] + 0.8, whistle(), 0.5)
    # 人口カウントアップのチック音
    for sid, rv in (('r5', 0.35), ('r4', 0.35), ('r3', 0.35), ('r2', 0.35), ('r1', R1_REVEAL), ('bonus', 0.35)):
        t0 = S[sid]['s'] + rv + 0.25 + 0.3
        for i in range(10):
            add(sfx, t0 + 1.1 * (1 - (1 - i / 10) ** 0.5), tick(), 0.12)

    norm = lambda x: x / (np.max(np.abs(x)) + 1e-9)
    return norm(music[:int(total * SR)]) * 0.9, norm(sfx[:int(total * SR)]) * 0.9

def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    m, s = generate(load_timing())
    os.makedirs(os.path.join(HERE, 'output'), exist_ok=True)
    write(os.path.join(HERE, 'output', 'bgm.wav'), m); write(os.path.join(HERE, 'output', 'sfx.wav'), s)
    print('wrote output/bgm.wav, output/sfx.wav', f'{len(m) / SR:.1f}s')
