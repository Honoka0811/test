# -*- coding: utf-8 -*-
"""BGM と効果音をプログラムで合成する(外部音源なし・権利フリー)。
BGM: Dマイナー / 90BPM のミステリアスなドキュメンタリー調(Dm–B♭–Gm–A)。
  低音ピアノの8分オスティナート + ストリングス風パッド + 低いドローン + 心音のようなキック + 時計の刻み + まばらなオルゴール。
  冒頭: ドローンが膨らむ → 「満洲国」で曲が始まる / 概要: ピアノと刻み / ランキング: 脈打つベースとビート(順位が上がるほど厚く)
  1位: ドローンだけにして溜め → 発表で低い弦の一撃と共に戻る / 番外編: 謎めいたオルゴール / 鉄道: 16分の刻み / あじあ号: フル / 結び: 静かに終わる
効果音: 耳に優しい音だけで構成(高域を削ったポン・シャラン・柔らかいウーッシュ)。音程は Dマイナーに合わせる。
タイミングは render.html と同じ値を使う。
単体実行: python3 music.py  → output/bgm.wav, output/sfx.wav
"""
import os, json, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 90
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.abspath(__file__))
R1_REVEAL = 1.5     # render.html と同じ
BONUS_STAMP = 4.3

PROG = [[62, 65, 69], [58, 62, 65], [55, 58, 62], [57, 61, 64]]   # Dm B♭ Gm A
ROOTS = [38, 34, 43, 33]
# ピアノのオスティナート(コードトーンの番号, 8分×8)
OSTINATO = [0, 2, 1, 2, 0, 2, 1, 2]
# 上位の順位で入る弦の対旋律(各小節 2分音符×2)
COUNTER = [[74, 72], [70, 69], [70, 67], [69, 73]]

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

RNG = np.random.default_rng(23)
def noise(dur): return RNG.standard_normal(int(dur * SR))

# ---------- 楽器 ----------
def piano(f, dur=1.2):
    """フェルトピアノ風: 倍音少なめ・柔らかいアタック"""
    t = tvec(dur)
    x = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.4)
         + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.2))
    return lp(x * np.exp(-t / 0.7) * np.minimum(1, t / 0.006), 2500)

def strings(notes, dur, bright=1200):
    """ストリングス風パッド: デチューンした鋸波を強めにローパス + ゆっくりした立ち上がりとビブラート"""
    t = tvec(dur); x = np.zeros_like(t)
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * t)
    for m in notes:
        for det in (-0.005, 0.0, 0.005):
            f = midi(m) * (1 + det)
            ph = 2 * np.pi * np.cumsum(f * vib) / SR
            for h in range(1, 8): x += np.sin(h * ph) / h
    env = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.6)
    return lp(x, bright) * env / (len(notes) * 6)

def drone(f, dur):
    t = tvec(dur)
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t)
    return x * (1 + 0.2 * np.sin(2 * np.pi * 0.15 * t)) * np.minimum(1, t / 1.0) * np.minimum(1, (dur - t) / 1.0)

def pulse_bass(f, dur):
    t = tvec(dur)
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return lp(x, 400) * np.minimum(1, t / 0.01) * np.exp(-t / 0.25)

def heartbeat(g2=0.6):
    """心音のような「ドッ・クン」"""
    out = np.zeros(int(0.6 * SR))
    for off, g in ((0, 1.0), (0.17, g2)):
        t = tvec(0.35); f = 45 + 45 * np.exp(-t / 0.03)
        add(out, off, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11), g)
    return out

def tick(g=1.0):
    """時計の刻み(高域を抑えた木のクリック)"""
    t = tvec(0.04)
    return lp(bp(noise(0.04), 1500, 4500), 5000) * np.exp(-t / 0.006) * g

def rim():
    t = tvec(0.12)
    return lp(bp(noise(0.12), 600, 2500), 3000) * np.exp(-t / 0.03) * 0.7 + 0.3 * np.sin(2 * np.pi * 420 * t) * np.exp(-t / 0.02)

def musicbox(f, dur=1.6):
    t = tvec(dur)
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t / 0.2)
    return lp(x * np.exp(-t / 0.6) * np.minimum(1, t / 0.003), 6000)

def low_hit(dur=2.5):
    """低い弦の一撃(1位の発表)"""
    t = tvec(dur)
    return strings([38, 50, 57], dur, 900) * np.exp(-t / 0.9) * 3 + np.sin(2 * np.pi * np.cumsum(40 + 30 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.5)

def glock(f, dur=1.0):
    t = tvec(dur)
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.15)
    return lp(x * np.exp(-t / 0.4) * np.minimum(1, t / 0.003), 7000)

def tom(f=110):
    t = tvec(0.35); fr = f * (1 + 0.3 * np.exp(-t / 0.03))
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.14)

# ---------- 効果音(やさしい音・Dマイナーに合わせる) ----------
def pon(f=440, big=False):
    dur = 1.0 if big else 0.6; t = tvec(dur)
    tone = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.18) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t / 0.12)
    thud = np.sin(2 * np.pi * np.cumsum(55 + 50 * np.exp(-t / 0.04)) / SR) * np.exp(-t / (0.25 if big else 0.15))
    return (0.6 * tone + 0.8 * thud) * np.minimum(1, t / 0.004)

def sparkle(base=74, n=5, gap=0.06):
    """シャラン: Dマイナーの上行アルペジオ"""
    notes = [0, 3, 7, 12, 15, 19, 24][:n]
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
    """冒頭: ピアノの低音が加速しながら上がっていく"""
    out = np.zeros(int((dur + 1.0) * SR)); t = 0.0; i = 0
    notes = [50, 53, 57, 62, 65, 69, 74]
    while t < dur:
        p = t / dur
        add(out, t, piano(midi(notes[i % 7] + 12 * (i // 7 % 2)), 0.8), 0.25 + 0.5 * p)
        t += lerp(0.2, 0.06, p); i += 1
    return out

def tom_roll(dur):
    out = np.zeros(int((dur + 0.5) * SR)); t = 0.0
    while t < dur:
        p = t / dur; add(out, t, tom(lerp(90, 130, p)), 0.25 + 0.6 * p)
        t += lerp(0.12, 0.05, p)
    return out

def whistle(dur=0.9):
    t = tvec(dur); env = np.minimum(1, t / 0.12) * np.minimum(1, (dur - t) / 0.3)
    x = sum(np.sin(2 * np.pi * f * t * (1 + 0.003 * np.sin(2 * np.pi * 5 * t))) for f in (midi(74), midi(77)))
    return lp(x, 2000) * env * 0.5

# ---------- 構成 ----------
def generate(timing):
    S = {s['id']: s for s in timing['scenes']}
    total = timing['total']
    n = int(total * SR) + SR
    drums, low, keys, pads, top, sfx = (np.zeros(n) for _ in range(6))
    kenv = np.zeros(n)

    def scene_at(t):
        for s in timing['scenes']:
            if s['s'] <= t < s['s'] + s['d']: return s['id'], t - s['s']
        return 'end', t - S['end']['s']

    # 全編に薄く流れるドローン(D)
    add(low, 0, drone(midi(26), total + 0.5), 0.35)

    start = 1.65  # タイトル「満洲国」が出る瞬間から曲が始まる
    nbars = int(np.ceil((total - start) / BAR)) + 1
    r1 = S['r1']['s']
    for b in range(nbars):
        bar_t = start + b * BAR
        ci = b % 4; chord = PROG[ci]; root = ROOTS[ci]
        sid0, _ = scene_at(bar_t)
        lvl0 = {'r5': 0, 'r4': 1, 'r3': 2, 'r2': 3, 'r1': 4, 'asia': 4, 'rail': 3}.get(sid0, 0)
        add(pads, bar_t, strings([m - 12 for m in chord], BAR + 0.6), 0.9)
        if lvl0 >= 2 or sid0 == 'asia':   # 上位では弦の対旋律
            for k, m in enumerate(COUNTER[ci]):
                add(pads, bar_t + k * BAR / 2, strings([m], BAR / 2 + 0.4, 1600), 0.35 + 0.05 * lvl0)
        for step in range(16):
            t = bar_t + step * BEAT / 4
            if t >= total: break
            sid, lt = scene_at(t)
            if sid == 'r1' and lt < R1_REVEAL: continue        # 1位の溜め: ドローンだけ
            lvl = {'r5': 0, 'r4': 1, 'r3': 2, 'r2': 3, 'r1': 4, 'asia': 4, 'rail': 3}.get(sid)
            hb = lambda g=1.0: (add(drums, t, heartbeat(), g), add(kenv, t, np.exp(-tvec(0.4) / 0.15)))
            # ピアノのオスティナート(8分)
            if step % 2 == 0 and sid not in ('bonus',):
                note = chord[OSTINATO[(step // 2) % 8]] - (12 if sid in ('hook', 'end') else 0)
                add(keys, t, piano(midi(note)), 0.5 if sid != 'end' else 0.4)
            if sid == 'hook':
                if step == 0: hb(0.7)
            elif sid == 'overview':
                if step == 0: hb(0.8)
                if step % 4 == 0: add(drums, t, tick(), 0.25)
            elif lvl is not None:
                if step in (0, 8): hb(0.9)
                if step in (4, 12): add(drums, t, rim(), 0.3 + 0.03 * lvl)
                if sid == 'rail': add(drums, t, tick(), 0.32 if step % 4 == 0 else 0.15)   # 汽車のような 16分の刻み
                elif step % 2 == 0: add(drums, t, tick(), 0.18 + 0.03 * lvl)
                if step % 2 == 0: add(low, t, pulse_bass(midi(root), BEAT / 2), 0.7)
                if lvl >= 3 and step in (2, 11) and (b % 2 == 0): add(top, t, musicbox(midi(chord[(step // 3) % 3] + 24)), 0.18)
            elif sid == 'bonus':
                if step == 0: hb(0.6)
                if step % 4 == 0: add(drums, t, tick(), 0.22)
                if step in (0, 3, 6, 10, 13): add(top, t, musicbox(midi(chord[(step // 2) % 3] + 12)), 0.3)   # 謎めいたオルゴール
            elif sid == 'end':
                if lt < 4.2 and step == 0: hb(0.5)
                if lt > 4.2 and step in (0, 6, 12): add(top, t, musicbox(midi(chord[(step // 6) % 3] + 12)), 0.22)

    duck = 1 - 0.3 * np.clip(kenv, 0, 1)
    music = 0.7 * drums + 0.6 * low * duck + 0.5 * keys + 0.55 * pads * duck + 0.6 * top
    tt = np.arange(n) / SR
    gate = np.where((tt >= r1) & (tt < r1 + R1_REVEAL), 0.3, 1.0)
    music *= lp(gate, 20, 1)
    add(music, r1 + R1_REVEAL, low_hit(), 0.5)
    music *= np.clip(tt / 0.2, 0, 1) * np.clip((total - tt) / 3.0, 0, 1)
    music = lp(music, 8000)

    # ---------- 効果音(控えめ) ----------
    add(sfx, 0.05, soft_riser(1.55), 0.6)
    add(sfx, 0.35, pon(midi(62)), 0.35); add(sfx, 0.8, pon(midi(65)), 0.35)
    add(sfx, 1.65, pon(midi(69), big=True), 0.6); add(sfx, 1.65, sparkle(74, 6), 0.45)
    for sid in ('overview', 'r5', 'r4', 'r3', 'r2', 'r1', 'bonus', 'rail', 'asia', 'end'):
        add(sfx, S[sid]['s'] - 0.3, soft_whoosh(0.45), 0.18)
    for i, sid in enumerate(('r5', 'r4', 'r3', 'r2')):
        add(sfx, S[sid]['s'] + 0.35, pon(midi([62, 65, 69, 72][i])), 0.55)    # 順位が上がるほど音程も上がる
    add(sfx, r1 + 0.05, tom_roll(R1_REVEAL - 0.1), 0.35)
    add(sfx, r1 + R1_REVEAL, pon(midi(74), big=True), 0.6); add(sfx, r1 + R1_REVEAL, sparkle(74, 7), 0.55)
    add(sfx, S['bonus']['s'] + 0.35, pon(midi(69)), 0.45)
    add(sfx, S['bonus']['s'] + BONUS_STAMP, pon(midi(57), big=True), 0.5)
    add(sfx, S['end']['s'] + 4.2, pon(midi(50), big=True), 0.45)
    for k_, base in ((2.3, 62), (5.2, 65), (9.0, 69)):
        add(sfx, S['rail']['s'] + k_, sparkle(base, 3, 0.08), 0.25)
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
