# -*- coding: utf-8 -*-
"""BGM を numpy だけで合成する(外部音源なし=権利フリー)。
シーンごとに雰囲気を変える: 導入=低音ドローン / 繁栄=明るいアルペジオ / 影・時限爆弾=時計の秒針 / 転落=太鼓 / 終章=静かな余韻
使い方: python3 bgm.py   → output/bgm.wav(timeline.js のシーン時刻に同期)
"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
BPM = 96.0
BEAT = 60.0 / BPM
BAR = BEAT * 4

def load_timeline():
    s = open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])

def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
def add(buf, t0, sig, g=1.0):
    s = int(t0 * SR)
    if s >= len(buf) or s < 0: return
    e = min(len(buf), s + len(sig)); buf[s:e] += sig[:e - s] * g
def env(n, a, r):
    e = np.ones(n, dtype=np.float32); a = min(int(a * SR), n // 2); r = min(int(r * SR), n // 2)
    if a: e[:a] = np.linspace(0, 1, a)
    if r: e[-r:] = np.linspace(1, 0, r)
    return e
def pad(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n, dtype=np.float32)
    for det in (-0.004, 0.0, 0.004):
        for h in range(1, 6):
            x += (1 / h ** 1.8) * np.sin(2 * np.pi * f * h * (1 + det) * t + rng.uniform(0, 6.28))
    return x * env(n, 0.9, 1.1)
def pluck(f, dur=1.4, bright=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + bright * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t / 0.32) * np.minimum(1, t / 0.004)).astype(np.float32)
def piano(f, dur=3.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum((1 / h ** 1.3) * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (0.9 + 0.5 * h)) for h in range(1, 7))
    return (x * np.minimum(1, t / 0.006)).astype(np.float32)
def taiko(rng, f0=85.0, dur=0.7):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 45 + (f0 - 45) * np.exp(-t / 0.08)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22)
    click = np.convolve(rng.standard_normal(n) * np.exp(-t / 0.012), np.ones(96) / 96, mode='same')
    return (body + 0.25 * click).astype(np.float32)
def boom(rng, dur=3.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 32 + 70 * np.exp(-t / 0.12)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    nz = np.convolve(rng.standard_normal(n) * np.exp(-t / 0.25), np.ones(200) / 200, mode='same')
    return (body + 0.5 * nz).astype(np.float32)
def tick(hi=False):
    n = int(0.05 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * (2600 if hi else 1900) * t) * np.exp(-t / 0.006)).astype(np.float32)
def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y
def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.72), (1877, 0.70), (2251, 0.68), (12007, 0.45))) / 4
    return (1 - mix) * x + mix * wet
def norm(x): return x / (np.max(np.abs(x)) + 1e-9)

# コード進行(MIDI ノート)
DARK = [[50, 57, 62, 65], [46, 53, 58, 62], [43, 50, 55, 58], [45, 52, 57, 61]]            # Dm  Bb  Gm  A
BRIGHT = [[53, 57, 60, 65], [48, 55, 60, 64], [50, 57, 62, 65], [46, 53, 58, 62]]          # F   C   Dm  Bb
END = [[50, 57, 62, 65], [46, 53, 58, 62], [53, 57, 60, 65], [48, 55, 60, 64]]             # Dm  Bb  F   C
MOOD = {'hook': DARK, 'miracle': BRIGHT, 'rise': BRIGHT, 'shadow': DARK, 'bomb': DARK, 'fall': DARK, 'japan': DARK, 'end': END}

def generate(tl=None, seed=3):
    tl = tl or load_timeline(); total = tl['duration']; rng = np.random.default_rng(seed)
    n = int(total * SR); L = {k: np.zeros(n, dtype=np.float32) for k in ('pad', 'bass', 'arp', 'piano', 'drum', 'tick', 'fx')}
    scene_at = lambda t: next((s for s in reversed(tl['scenes']) if t >= s['t0']), tl['scenes'][0])
    for b in range(int(np.ceil(total / BAR))):
        t0 = b * BAR; sc = scene_at(t0 + 0.01); sid = sc['id']; chord = MOOD[sid][b % 4]; prog = (t0 - sc['t0']) / max(1e-6, sc['t1'] - sc['t0'])
        add(L['pad'], t0, sum(pad(midi(m), BAR + 1.0, rng) * (1.0 if i < 3 else 0.5) for i, m in enumerate(chord)), {'hook': 0.6, 'bomb': 0.5, 'shadow': 0.7}.get(sid, 1.0))
        f = midi(chord[0] - 12); tt = np.arange(int((BAR + 1.0) * SR)) / SR
        add(L['bass'], t0, ((np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt)) * env(len(tt), 0.6, 1.0)).astype(np.float32))
        if sid in ('miracle', 'rise'):          # 繁栄: 8 分のアルペジオ+軽い拍
            pat = [0, 2, 1, 2, 3, 2, 1, 2]
            for k, p in enumerate(pat):
                add(L['arp'], t0 + k * BEAT / 2, pluck(midi(chord[p] + 12)), 0.6 + 0.4 * (k % 2 == 0))
                if sid == 'rise' and prog > 0.25: add(L['arp'], t0 + k * BEAT / 2, pluck(midi(chord[p] + 24), 0.9, 0.2), 0.35)
            if sid == 'rise':
                for k in (0, 2): add(L['drum'], t0 + k * BEAT, taiko(rng, 80), 0.45 + 0.3 * prog)
        elif sid == 'shadow':                   # 影: まばらなピアノ
            add(L['piano'], t0, piano(midi(chord[2] + 12)), 0.9); add(L['piano'], t0 + 2.5 * BEAT, piano(midi(chord[1] + 12)), 0.6)
        elif sid == 'fall':                     # 転落: 太鼓
            for k, g in ((0, 1.0), (1.5, 0.5), (2, 0.85), (3.5, 0.45)): add(L['drum'], t0 + k * BEAT, taiko(rng, 85 - 6 * (k > 1)), g * (0.6 + 0.4 * prog))
            for k in range(8):
                if k % 2 == 0: add(L['arp'], t0 + k * BEAT / 2, pluck(midi(chord[(k // 2) % 3] + 12), 1.0, 0.5), 0.5)
        elif sid == 'japan':
            add(L['piano'], t0, piano(midi(chord[2] + 12)), 0.8); add(L['piano'], t0 + 2 * BEAT, piano(midi(chord[3] + 12)), 0.55)
            add(L['drum'], t0, taiko(rng, 70), 0.35)
        elif sid == 'end':
            for k, p in enumerate([0, 1, 2, 3]): add(L['piano'], t0 + k * BEAT, piano(midi(chord[p] + 12), 2.4), 0.75 if k == 0 else 0.5)
    # 秒針: 「時限爆弾」の章と、日本の章の終盤
    S = {s['id']: s for s in tl['scenes']}
    for a, b, g in ((S['bomb']['t0'], S['bomb']['t1'], 1.0), (S['shadow']['t0'], S['shadow']['t1'], 0.35), (S['japan']['t1'] - 8.0, S['japan']['t1'], 0.8)):
        k = 0; t = a
        while t < b: add(L['tick'], t, tick(k % 2 == 1), g * min(1.0, (t - a) / 2 + 0.3)); t += 0.5; k += 1
    # 効果音: 冒頭の年号、破産申請のスタンプ、章の変わり目
    ln = tl['lines']
    for t, g in ((ln[0]['t0'], 1.0), (ln[0]['chunks'][-1]['t0'] + 0.1, 0.9), (ln[21]['chunks'][-1]['t0'] + 0.3, 1.0), (ln[26]['t0'] + 0.45, 0.7), (S['shadow']['t0'], 0.6), (ln[17]['t0'], 0.6)):
        add(L['fx'], t, boom(rng), g)
    mix = (0.50 * norm(L['pad']) + 0.30 * norm(L['bass']) + 0.30 * reverb(norm(L['arp']), 0.35) + 0.42 * reverb(norm(L['piano']), 0.45)
           + 0.55 * norm(L['drum']) + 0.16 * reverb(norm(L['tick']), 0.25) + 0.85 * reverb(norm(L['fx']), 0.3))
    mix = reverb(mix, 0.15) * env(n, 0.3, 4.0)
    return (norm(mix) * 0.9).astype(np.float32)

if __name__ == '__main__':
    x = generate(); out = os.path.join(HERE, 'output', 'bgm.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
