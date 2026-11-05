# -*- coding: utf-8 -*-
"""BGM と効果音を numpy/scipy だけで合成し、ナレーションとミックスする(外部音源なし・権利フリー)。
BGM: Cメジャー / 124BPM のアップビートなポップ(C–G–Am–F)。
  ・冒頭「つまらない…」は時計の秒針+こもったパッドだけ → 「習慣10選!」でドロップ(全楽器イン)
  ・5位以降はリードメロディが加わって盛り上がる
  ・「そして第1位は…」でドラムが止まり、ドラムロール → 1位発表で再ドロップ
効果音: 秒針 / ライザー / クラッシュ / ランク表示のポップ / 場面転換のシュッ / キラキラ / ドラムロール / ファンファーレ
使い方: python3 music.py   (output/timeline.json と output/narration.wav が必要)
"""
import os, json, wave
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
BPM = 124
BEAT = 60 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(11)

PROG = [  # (ベースのルート, コード構成音) MIDI
    (36, [60, 64, 67, 72]),  # C
    (43, [59, 62, 67, 71]),  # G
    (45, [60, 64, 69, 72]),  # Am
    (41, [60, 65, 69, 72]),  # F
]
# リード(2小節×2 のモチーフ、C メジャーペンタ)。(拍位置, MIDI, 長さ拍)
LEAD = [(0, 76, .5), (.5, 79, .5), (1, 81, 1), (2.5, 79, .5), (3, 76, 1),
        (4, 74, .5), (4.5, 76, .5), (5, 79, 1.5), (7, 74, .5), (7.5, 72, .5),
        (8, 76, .5), (8.5, 79, .5), (9, 81, 1), (10.5, 84, .5), (11, 81, 1),
        (12, 79, .5), (12.5, 76, .5), (13, 74, 1), (14, 72, 2)]


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x).astype(np.float32)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x).astype(np.float32)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], 'band', fs=SR, output='sos'), x).astype(np.float32)
def noise(d): return rng.standard_normal(int(d * SR)).astype(np.float32)
def norm(x, p=1.0): return (x / (np.max(np.abs(x)) + 1e-9) * p).astype(np.float32)


def add(buf, t0, sig, g=1.0):
    s = int(round(t0 * SR))
    if s < 0: sig, s = sig[-s:], 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += g * sig[:e - s]


def adsr(n, a=0.005, d=0.1, s=0.6, r=0.1):
    env = np.full(n, s, dtype=np.float32)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = min(na, n); env[:na] = np.linspace(0, 1, na)
    nd = min(nd, n - na); env[na:na + nd] = np.linspace(1, s, nd)
    nr = min(nr, n); env[n - nr:] *= np.linspace(1, 0, nr)
    return env

# ---------------- 楽器 ----------------
def kick():
    t = tt(0.32); f = 48 + 110 * np.exp(-t / 0.035)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13) + 0.3 * lp(noise(0.32), 3000) * np.exp(-t / 0.004))

def clap():
    n = noise(0.25); t = tt(0.25)
    env = sum(np.exp(-np.clip(t - o, 0, None) / 0.006) * (t >= o) for o in (0, 0.011, 0.022)) * 0.6 + np.exp(-t / 0.07) * (t > 0.03)
    return norm(bp(n, 900, 5000) * env)

def hat(d=0.05):
    t = tt(d); return norm(hp(noise(d), 7000) * np.exp(-t / (d / 4)))

def snare():
    t = tt(0.18)
    return norm(0.6 * bp(noise(0.18), 1500, 7000) * np.exp(-t / 0.05) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04))

def saw(f, d, harm=10):
    t = tt(d); return sum(((-1) ** (k + 1)) / k * np.sin(2 * np.pi * f * k * t) for k in range(1, harm + 1)).astype(np.float32)

def bass_note(m, d):
    x = saw(midi(m), d, 8) + 0.6 * np.sin(2 * np.pi * midi(m) * tt(d))
    return lp(x, 500) * adsr(len(x), 0.004, 0.12, 0.55, 0.04)

def pluck_chord(notes, d=0.28):
    x = sum(saw(midi(m) * (1 + det), d, 12) for m in notes for det in (-0.003, 0.003))
    t = tt(d); return lp(x * np.exp(-t / 0.09), 4200)

def pad_chord(notes, d):
    t = tt(d)
    x = sum(np.sin(2 * np.pi * midi(m - 12) * (1 + det) * t) + 0.3 * np.sin(2 * np.pi * midi(m) * (1 + det) * t)
            for m in notes for det in (-0.004, 0.0, 0.004))
    return (x * adsr(len(t), 0.25, 0.1, 1.0, 0.3)).astype(np.float32)

def bell(m, d=0.6, bright=1.0):
    t = tt(d); f = midi(m)
    mod = bright * 2.2 * np.exp(-t / 0.15) * np.sin(2 * np.pi * f * 3.5 * t)
    return (np.sin(2 * np.pi * f * t + mod) * np.exp(-t / (d / 3)) * adsr(len(t), 0.002, 0.01, 1, 0.02)).astype(np.float32)


def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.25):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.7), (1877, 0.68), (2251, 0.66), (2671, 0.62))) / 4
    return ((1 - mix) * x + mix * lp(wet, 6000)).astype(np.float32)

# ---------------- BGM ----------------
def groove(n, anchor, start, end, lead_from=None):
    """anchor 秒を1小節目の頭とするビートで、start〜end 秒の各パートを生成"""
    st = {k: np.zeros(n, dtype=np.float32) for k in ('kick', 'clap', 'hat', 'bass', 'stab', 'pad', 'lead')}
    K, C, H, Hs, SN = kick(), clap(), hat(), hat(0.025), snare()
    b0 = int(np.floor((start - anchor) / BAR)); b1 = int(np.ceil((end - anchor) / BAR))
    for b in range(b0, b1):
        t0 = anchor + b * BAR
        root, ch = PROG[b % 4]
        add(st['pad'], t0, pad_chord(ch, BAR + 0.3))
        for k in range(4):
            add(st['kick'], t0 + k * BEAT, K)
            add(st['hat'], t0 + (k + 0.5) * BEAT, H, 0.8)
            add(st['hat'], t0 + (k + 0.25) * BEAT, Hs, 0.25)
            add(st['hat'], t0 + (k + 0.75) * BEAT, Hs, 0.3)
        add(st['clap'], t0 + BEAT, C); add(st['clap'], t0 + 3 * BEAT, C)
        if b % 4 == 3:  # 4小節ごとのフィル
            for k in (3.5, 3.75): add(st['clap'], t0 + k * BEAT, SN, 0.5)
        for k, off in enumerate((0, 0, 12, 0, 0, 12, 0, 7)):
            add(st['bass'], t0 + k * BEAT / 2, bass_note(root + off, BEAT / 2 * 0.9))
        for k in (0, 0.75, 1.5, 2.5, 3.0, 3.5):
            add(st['stab'], t0 + k * BEAT, pluck_chord(ch))
        if lead_from is not None and t0 >= lead_from - 1e-3:
            for pos, m, d in LEAD:
                if (b % 4) * 4 <= pos < (b % 4) * 4 + 4:
                    add(st['lead'], t0 + (pos - (b % 4) * 4) * BEAT, bell(m, d * BEAT + 0.35, 0.8))
    return st


def mask(n, segs, fade=0.03):
    """segs = [(開始秒, 終了秒, ゲイン)] から滑らかなゲイン曲線を作る"""
    m = np.zeros(n, dtype=np.float32)
    for a, b, g in segs:
        m[int(max(a, 0) * SR):int(min(b * SR, n))] = g
    k = max(1, int(fade * SR))
    return np.convolve(m, np.ones(k) / k, mode='same').astype(np.float32)


def build(tl):
    T = tl['duration']; n = int(T * SR)
    sc = {s['type'] + str(s.get('rank', '')): s for s in tl['scenes']}
    drop = tl['drop']; teaser = sc['teaser']['start']; first = sc['rank1']['start']
    lead_from = sc['rank5']['start']
    # 1位までは drop を基準、1位以降は 1位の頭を基準に拍を取り直す
    A = groove(n, drop, 0, teaser + BAR, lead_from=lead_from)
    B = groove(n, first, first, T, lead_from=first)
    main = mask(n, [(drop, teaser + 0.05, 1)])
    post = mask(n, [(first, T, 1)])
    intro = mask(n, [(0, drop, 1)], 0.01)
    gains = dict(kick=.9, clap=.55, hat=.35, bass=.6, stab=.33, pad=.22, lead=.3)
    music = np.zeros(n, dtype=np.float32)
    for k, g in gains.items():
        music += g * (A[k] * main + B[k] * post)
    # ティーザー: パッドだけ残してローパス
    tease = mask(n, [(teaser, first, 1)], 0.15)
    music += 0.12 * lp(A['pad'] + B['pad'], 700) * tease
    # 冒頭: こもったパッドのみ(つまらない感)
    music += 0.14 * lp(A['pad'], 450) * intro
    music = reverb(music, 0.15)
    music *= mask(n, [(0, T - 2.2, 1)], 0.05) + mask(n, [(T - 2.2, T, 1)], 0.05) * np.clip((T - np.arange(n) / SR) / 2.2, 0, 1)
    return norm(music, 0.9)


# ---------------- 効果音 ----------------
def whoosh(d=0.45):
    t = tt(d); x = noise(d); out = np.zeros_like(x)
    for i, f in enumerate(np.linspace(600, 5000, 12)):
        seg = slice(int(i * len(x) / 12), int((i + 1) * len(x) / 12))
        out[seg] = bp(x, f * 0.7, f * 1.3)[seg]
    return norm(out * np.sin(np.pi * t / d) ** 2)

def pop():
    t = tt(0.18); f = 900 * np.exp(-t / 0.03) + 220
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05))

def sparkle():
    out = np.zeros(int(0.9 * SR), dtype=np.float32)
    for i, m in enumerate((84, 88, 91, 96)): add(out, i * 0.055, bell(m, 0.6, 0.5), 0.6)
    return norm(out)

def crash(d=2.2):
    t = tt(d); return norm(hp(noise(d), 4000) * np.exp(-t / 0.6) + 0.3 * bp(noise(d), 300, 3000) * np.exp(-t / 0.1))

def riser(d):
    t = tt(d); x = noise(d); out = np.zeros_like(x)
    for i, f in enumerate(np.geomspace(300, 8000, 16)):
        seg = slice(int(i * len(x) / 16), int((i + 1) * len(x) / 16))
        out[seg] = bp(x, f * 0.8, f * 1.25)[seg]
    return norm(out * (t / d) ** 2)

def tick():
    t = tt(0.04); return norm(hp(noise(0.04), 3000) * np.exp(-t / 0.004) + 0.5 * np.sin(2 * np.pi * 2500 * t) * np.exp(-t / 0.006))

def fanfare():
    out = np.zeros(int(2.0 * SR), dtype=np.float32)
    for i, (m, w) in enumerate(((72, 0), (76, 0.09), (79, 0.18), (84, 0.3))):
        add(out, w, saw(midi(m), 1.6, 8) * adsr(int(1.6 * SR), 0.01, 0.2, 0.5, 0.6) * 0.5)
        add(out, w, bell(m + 12, 1.2), 0.5)
    return norm(lp(out, 5000))

def thud():
    t = tt(0.5); f = 40 + 60 * np.exp(-t / 0.05)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18))


def build_sfx(tl):
    T = tl['duration']; n = int(T * SR); x = np.zeros(n, dtype=np.float32)
    drop = tl['drop']
    # 冒頭: 退屈な秒針
    for k in range(int(drop / 0.5)):
        add(x, 0.05 + k * 0.5, tick(), 0.35)
    add(x, drop - 0.95, riser(0.95), 0.35)
    add(x, drop, crash(), 0.5); add(x, drop, thud(), 0.55)
    add(x, drop + 0.05, sparkle(), 0.3)
    for s in tl['scenes']:
        if s['type'] == 'rank':
            add(x, s['start'] - 0.22, whoosh(), 0.45)
            add(x, s['start'] + 0.12, pop(), 0.5)
            reason = [c for c in s['chunks'] if c['kind'] == 'reason'][0]
            add(x, reason['s'] - 0.05, sparkle(), 0.22)
            if s['rank'] == 1:
                add(x, s['start'], crash(2.8), 0.6); add(x, s['start'], thud(), 0.6)
                add(x, s['start'] + 0.05, fanfare(), 0.45)
        elif s['type'] == 'teaser':
            a, b = s['start'] + 0.25, s['end']
            t = a; k = 0
            while t < b - 0.02:  # だんだん速く・大きくなるドラムロール
                p = (t - a) / (b - a)
                add(x, t, snare(), 0.18 + 0.5 * p ** 1.5)
                t += 0.11 - 0.065 * p; k += 1
            add(x, b - 1.6, riser(1.6), 0.3)
        elif s['type'] == 'outro':
            add(x, s['start'] - 0.22, whoosh(), 0.4)
            add(x, s['chunks'][0]['s'], sparkle(), 0.3)
    return x


def read_wav(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def write_wav(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
    voice = read_wav(os.path.join(OUT, 'narration.wav'))
    n = len(voice)
    music = build(tl)[:n]; sfx = build_sfx(tl)[:n]
    write_wav(os.path.join(OUT, 'bgm.wav'), music)
    write_wav(os.path.join(OUT, 'sfx.wav'), norm(sfx, 0.9))
    # ナレーションに合わせて BGM を下げる(ダッキング)
    hop = SR // 50
    rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(rms)
    for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.94)  # リリース ≈ 0.3秒
    env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
    speech = np.clip(env / 0.08, 0, 1)
    g = 0.42 - (0.42 - 0.2) * speech
    g = np.convolve(g, np.ones(SR // 20) / (SR // 20), mode='same')
    mix = voice + music * g + sfx * 0.55
    mix = mix / max(1.0, np.max(np.abs(mix)) / 0.97)
    write_wav(os.path.join(OUT, 'mix.wav'), mix)
    print('wrote output/bgm.wav, sfx.wav, mix.wav', f'{n / SR:.2f}s')
