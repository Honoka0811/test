# -*- coding: utf-8 -*-
"""BGM と効果音をプログラムで合成する(外部音源なし・権利フリー)。
BGM: Cメジャー / 104BPM の明るく軽快なポップ(C–G–Am–F)。マリンバのメロディ + グロッケン + 柔らかいドラム + 丸いベース。
  冒頭: やさしいライザー → メロディ開始 / 概要: 軽めのビート / ランキング: フル(順位が上がるほど楽器が増える)
  1位: いったん静かにして溜め → 発表で全員集合 / 番外編: 弾むハーフタイム / 鉄道: 汽車風のシェイカー / あじあ号: フル / 結び: しっとり
効果音: 耳に優しい音だけで構成(高域を削ったポン・シャラン・柔らかいウーッシュ)。タイミングは render.html と同じ値を使う。
単体実行: python3 music.py  → output/bgm.wav, output/sfx.wav
"""
import os, json, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 104
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.abspath(__file__))
R1_REVEAL = 1.5     # render.html と同じ
BONUS_STAMP = 4.3

PROG = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]   # C G Am F
ROOTS = [48, 43, 45, 41]
# 4小節のメロディ(16分音符の位置, MIDIノート, 長さ[拍])。覚えやすい上行→下行の形
MELODY = [
    [(0, 76, 1), (4, 79, 1), (8, 76, .5), (10, 74, .5), (12, 72, 1)],
    [(0, 74, 1), (4, 71, 1), (8, 74, 1.5), (14, 79, .5)],
    [(0, 76, 1), (4, 72, 1), (8, 81, 1), (12, 79, 1)],
    [(0, 77, 1), (4, 76, .5), (6, 74, .5), (8, 72, 2)],
]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tvec(dur): return np.arange(int(dur * SR)) / SR
def lp(x, f, order=2): return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)
def lerp(a, b, p): return a + (b - a) * p

def add(buf, t0, sig, g=1.0):
    s = int(t0 * SR)
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += g * sig[:e - s]

def load_timing():
    with open(os.path.join(HERE, 'timing.js'), encoding='utf-8') as f:
        src = f.read()
    return json.loads(src[src.index('{'): src.rindex('}') + 1])

RNG = np.random.default_rng(5)
def noise(dur): return RNG.standard_normal(int(dur * SR))

# ---------- 楽器(どれも高域を抑えた丸い音) ----------
def marimba(f, dur=0.6):
    t = tvec(dur)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.28) + 0.25 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.05)
    return x * np.minimum(1, t / 0.002)

def glock(f, dur=1.0):
    t = tvec(dur)
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.15)
    return lp(x * np.exp(-t / 0.4) * np.minimum(1, t / 0.003), 7000)

def epiano(chord, dur):
    t = tvec(dur); x = np.zeros_like(t)
    for m in chord:
        f = midi(m)
        x += (np.sin(2 * np.pi * f * t) + 0.15 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.9)
    return x * np.minimum(1, t / 0.004) * np.minimum(1, (dur - t) / 0.08) / len(chord)

def pad(chord, dur):
    t = tvec(dur); x = np.zeros_like(t)
    for m in chord:
        for det in (-0.003, 0.003):
            f = midi(m) * (1 + det)
            x += np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 0.5)
    return lp(x, 1500) * env / (len(chord) * 2)

def bass(f, dur):
    t = tvec(dur)
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return x * np.minimum(1, t / 0.008) * np.minimum(1, (dur - t) / 0.03) * np.exp(-t / 0.6)

def kick():
    t = tvec(0.3); f = 50 + 70 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)

def snap():
    """指パッチン風の柔らかいスネア代わり"""
    t = tvec(0.15)
    return lp(bp(noise(0.15), 800, 3500), 4000) * np.exp(-t / 0.035) * 0.8 + 0.3 * np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.02)

def shaker(g=1.0):
    t = tvec(0.08); return lp(hp(noise(0.08), 3000), 8000) * np.exp(-t / 0.02) * np.sin(np.pi * np.clip(t / 0.08, 0, 1)) ** 0.5 * g

def tom(f=110):
    t = tvec(0.35); fr = f * (1 + 0.3 * np.exp(-t / 0.03))
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.14)

# ---------- 効果音(やさしい音) ----------
def pon(f=520, big=False):
    """順位発表の「ポン」: 丸いサイン + 低いドン"""
    dur = 1.0 if big else 0.6; t = tvec(dur)
    tone = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.18) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t / 0.12)
    thud = np.sin(2 * np.pi * np.cumsum(55 + 50 * np.exp(-t / 0.04)) / SR) * np.exp(-t / (0.25 if big else 0.15))
    return (0.6 * tone + 0.8 * thud) * np.minimum(1, t / 0.004)

def sparkle(base=72, n=5, gap=0.06):
    """シャラン: グロッケンの上行アルペジオ"""
    notes = [0, 4, 7, 12, 16, 19, 24][:n]
    out = np.zeros(int((gap * n + 1.2) * SR))
    for i, d in enumerate(notes):
        add(out, i * gap, glock(midi(base + d), 1.1), 0.5)
    return out

def soft_whoosh(dur=0.5):
    t = tvec(dur); n = noise(dur); out = np.zeros_like(n); seg = 512
    for i in range(0, len(n), seg):
        p = i / len(n); fc = 250 + 1500 * np.sin(np.pi * p)
        out[i:i + seg] = bp(n[max(0, i - 2048): i + seg], fc * 0.7, fc * 1.4)[-len(n[i:i + seg]):]
    return out * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2

def soft_riser(dur):
    """やさしいライザー: マリンバの上行アルペジオが加速"""
    out = np.zeros(int((dur + 0.6) * SR)); t = 0.0; i = 0
    notes = [60, 64, 67, 72, 76, 79, 84]
    while t < dur:
        p = t / dur
        add(out, t, marimba(midi(notes[i % 7] + 12 * (i // 7 % 2))), 0.25 + 0.5 * p)
        t += lerp(0.16, 0.05, p); i += 1
    return out

def tom_roll(dur):
    out = np.zeros(int((dur + 0.5) * SR)); t = 0.0
    while t < dur:
        p = t / dur; add(out, t, tom(lerp(95, 140, p)), 0.25 + 0.6 * p)
        t += lerp(0.12, 0.05, p)
    return out

def whistle(dur=0.9):
    t = tvec(dur); env = np.minimum(1, t / 0.12) * np.minimum(1, (dur - t) / 0.3)
    x = sum(np.sin(2 * np.pi * f * t * (1 + 0.003 * np.sin(2 * np.pi * 5 * t))) for f in (midi(76), midi(79)))
    return lp(x, 2000) * env * 0.5

# ---------- 構成 ----------
def generate(timing):
    S = {s['id']: s for s in timing['scenes']}
    total = timing['total']
    n = int(total * SR) + SR
    drums, low, keys, mel, pads, sfx = (np.zeros(n) for _ in range(6))
    kenv = np.zeros(n)

    def scene_at(t):
        for s in timing['scenes']:
            if s['s'] <= t < s['s'] + s['d']: return s['id'], t - s['s']
        return 'end', t - S['end']['s']

    start = 1.65  # タイトル「満洲国」が出る瞬間から曲が始まる
    nbars = int(np.ceil((total - start) / BAR)) + 1
    for b in range(nbars):
        bar_t = start + b * BAR
        ci = b % 4; chord = PROG[ci]; root = ROOTS[ci]
        sid0, lt0 = scene_at(bar_t)
        pg = {'end': 0.7, 'hook': 0.6, 'overview': 0.5, 'bonus': 0.35}.get(sid0, 0.4)
        add(pads, bar_t, pad(chord, BAR + 0.4), pg)
        for step in range(16):
            t = bar_t + step * BEAT / 4
            if t >= total: break
            sid, lt = scene_at(t)
            if sid == 'r1' and lt < R1_REVEAL: continue         # 1位の溜め: 静かに
            lvl = {'r5': 0, 'r4': 1, 'r3': 2, 'r2': 3, 'r1': 4, 'asia': 4, 'rail': 3}.get(sid)
            k = lambda g=1.0: (add(drums, t, kick(), g), add(kenv, t, np.exp(-tvec(0.25) / 0.1)))
            if sid == 'hook':
                if step == 0: k(0.7)
                if step % 4 == 0: add(keys, t, epiano(chord, BEAT * 0.95), 0.5)
                if step % 2 == 0: add(mel, t, marimba(midi(chord[(step // 2) % 3] + 12)), 0.35)
            elif sid == 'overview':
                if step in (0, 8): k(0.8)
                if step in (4, 12): add(drums, t, snap(), 0.35)
                if step % 2 == 0: add(drums, t, shaker(), 0.18)
                if step in (0, 6, 8, 14): add(low, t, bass(midi(root - 12), BEAT * 0.7), 0.8)
                if step % 4 == 2: add(keys, t, epiano(chord, BEAT * 0.5), 0.45)
                for (pos, note, ln) in MELODY[ci]:
                    if pos == step: add(mel, t, marimba(midi(note - 12), 0.5), 0.3)   # 1オクターブ下で控えめに予告
            elif lvl is not None:
                if step in (0, 8) or (step == 10 and lvl >= 2): k(0.9)
                if step in (4, 12): add(drums, t, snap(), 0.45)
                if sid == 'rail':
                    add(drums, t, shaker(), 0.32 if step % 4 in (0, 3) else 0.12)   # 汽車のリズム
                elif step % 2 == 0:
                    add(drums, t, shaker(), 0.2 + 0.03 * lvl)
                if step in (0, 3, 6, 8, 11, 14): add(low, t, bass(midi(root - 12 + (12 if step in (6, 14) else 0)), BEAT * 0.6), 0.8)
                if step % 4 == 2: add(keys, t, epiano(chord, BEAT * 0.5), 0.45)
                for (pos, note, ln) in MELODY[ci]:
                    if pos == step:
                        add(mel, t, marimba(midi(note), 0.4 + 0.3 * ln), 0.55)
                        if lvl >= 2: add(mel, t, glock(midi(note + 12)), 0.12 + 0.03 * lvl)   # 上位ほどキラキラ
            elif sid == 'bonus':
                if step == 0: k(0.8)
                if step == 8: add(drums, t, snap(), 0.4)
                if step % 4 == 0: add(drums, t, shaker(), 0.15)
                if step in (0, 8): add(low, t, bass(midi(root - 12), BEAT * 1.5), 0.7)
                if step % 3 == 0: add(mel, t, marimba(midi(chord[(step // 3) % 3] + 12)), 0.35)
            elif sid == 'end':
                if lt < 4.2:
                    if step == 0: k(0.5)
                    if step % 4 == 0: add(keys, t, epiano(chord, BEAT * 0.95), 0.45)
                if step % 4 == 0: add(mel, t, marimba(midi(chord[(step // 4) % 3] + 12), 0.9), 0.25)

    duck = 1 - 0.35 * np.clip(kenv, 0, 1)      # 軽いポンピング
    music = 0.6 * drums + 0.5 * low * duck + 0.35 * keys * duck + 0.55 * mel + 0.5 * pads * duck
    tt = np.arange(n) / SR
    r1 = S['r1']['s']
    gate = np.where((tt >= r1) & (tt < r1 + R1_REVEAL), 0.35, 1.0)
    music *= lp(gate, 20, 1)
    music *= np.clip(tt / 0.2, 0, 1) * np.clip((total - tt) / 3.0, 0, 1)
    music = lp(music, 9000)

    # ---------- 効果音(控えめ) ----------
    add(sfx, 0.05, soft_riser(1.55), 0.6)
    add(sfx, 0.35, pon(392), 0.35); add(sfx, 0.8, pon(440), 0.35)
    add(sfx, 1.65, pon(523, big=True), 0.6); add(sfx, 1.65, sparkle(72, 6), 0.5)
    for sid in ('overview', 'r5', 'r4', 'r3', 'r2', 'r1', 'bonus', 'rail', 'asia', 'end'):
        add(sfx, S[sid]['s'] - 0.3, soft_whoosh(0.45), 0.18)
    for i, sid in enumerate(('r5', 'r4', 'r3', 'r2')):
        add(sfx, S[sid]['s'] + 0.35, pon(midi(67 + i * 2)), 0.55)        # 順位が上がるほど音程も上がる
    add(sfx, r1 + 0.05, tom_roll(R1_REVEAL - 0.1), 0.35)
    add(sfx, r1 + R1_REVEAL, pon(523, big=True), 0.6); add(sfx, r1 + R1_REVEAL, sparkle(72, 7), 0.6)
    add(sfx, S['bonus']['s'] + 0.35, pon(midi(76)), 0.45)
    add(sfx, S['bonus']['s'] + BONUS_STAMP, pon(330, big=True), 0.5)
    add(sfx, S['end']['s'] + 4.2, pon(262, big=True), 0.45)
    for k_ in (2.3, 5.2, 9.0):
        add(sfx, S['rail']['s'] + k_, sparkle(67 + int(k_), 3, 0.08), 0.25)
    add(sfx, S['asia']['s'] + 0.8, whistle(), 0.35)
    sfx = lp(sfx, 8000)

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
