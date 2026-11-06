# -*- coding: utf-8 -*-
"""BGM(自作・numpy 合成)と効果音を作り、ナレーションとミックスする。
BGM: 128BPM / Cメジャー / 王道進行(F-G-Em-Am)のアップテンポなフューチャーポップ。
  ・冒頭0秒からビートを鳴らしてつかむ
  ・第1位の前でブレイク(ドラム停止+ライザー)→「住所は東京都!!」で再ドロップ
  ・ナレーション中は自動ダッキング
使い方: python3 audio.py  → output/bgm.wav, output/sfx.wav, output/mix.wav
"""
import os, json, wave
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
BPM = 128.0
BEAT = 60 / BPM
rng = np.random.default_rng(7)

def lp(x, f, o=2): return sosfilt(butter(o, f / (SR / 2), 'low', output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f / (SR / 2), 'high', output='sos'), x)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a / (SR / 2), b / (SR / 2)], 'band', output='sos'), x)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def env(n, a, d, sustain=0.0, rel=None):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1) * (sustain + (1 - sustain) * np.exp(-t / d))
    if rel:  # 末尾リリース
        r = int(rel * SR); e[-r:] *= np.linspace(1, 0, r)
    return e
def saw(f, n, ph=0.0):
    p = (ph + f * np.arange(n) / SR) % 1.0
    return 2 * p - 1

def add(buf, x, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf): return
    x = x[:len(buf) - i]
    buf[i:i + len(x)] += x * gain

# ---------- 楽器 ----------
def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    x += 0.4 * hp(rng.standard_normal(n), 3000) * np.exp(-t / 0.004)
    return np.tanh(x * 1.6)
def clap():
    n = int(0.25 * SR); t = np.arange(n) / SR
    no = bp(rng.standard_normal(n), 900, 5000)
    e = np.exp(-t / 0.06)
    for k in (0.0, 0.011, 0.022): e += 0.6 * np.exp(-np.maximum(t - k, 0) / 0.004) * (t >= k)
    return no * e * 0.5
def hat(open_=False):
    n = int((0.22 if open_ else 0.05) * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t / (0.07 if open_ else 0.012)) * 0.35
def supersaw(midi, n):
    x = np.zeros(n)
    for d in (-0.12, -0.05, 0, 0.06, 0.13):
        x += saw(mtof(midi + d), n, rng.random())
    return x / 5
def pluck(midi, n):
    t = np.arange(n) / SR; f = mtof(midi)
    x = (np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * 2 * f * t) * 0.3 + saw(f, n) * 0.3)
    return lp(x, 5000) * np.exp(-t / 0.18)
def bell(midi, n):
    t = np.arange(n) / SR; f = mtof(midi)
    m = np.sin(2 * np.pi * f * 3.5 * t) * 2.2 * np.exp(-t / 0.2)
    return np.sin(2 * np.pi * f * t + m) * np.exp(-t / 0.5)

# 王道進行 F - G - Em - Am (1小節ずつ)
CHORDS = [(53, [65, 69, 72, 76]), (55, [67, 71, 74, 77]), (52, [64, 67, 71, 74]), (57, [64, 69, 72, 76])]
# リードのフック(16分単位: (開始16分, 長さ16分, midi))  2小節×2
LEAD = [(0, 2, 81), (2, 2, 79), (4, 2, 76), (6, 4, 79), (10, 2, 81), (12, 4, 84),
        (16, 2, 83), (18, 2, 81), (20, 2, 79), (22, 4, 76), (26, 2, 74), (28, 4, 76),
        (32, 2, 81), (34, 2, 79), (36, 2, 76), (38, 4, 79), (42, 2, 81), (44, 2, 84), (46, 2, 86),
        (48, 3, 88), (51, 1, 86), (52, 2, 84), (54, 2, 83), (56, 8, 81)]

def section(dur, drums=True, lead=True, start_bar=0):
    """dur 秒ぶんのループ本体(ステレオ)。kick に合わせたサイドチェイン付き"""
    n = int(dur * SR) + SR
    L = np.zeros(n); R = np.zeros(n); kick_env = np.zeros(n)
    s16 = BEAT / 4
    bars = int(dur / (BEAT * 4)) + 2
    K, C = kick(), clap()
    for b in range(bars):
        t0 = b * BEAT * 4
        root, notes = CHORDS[(b + start_bar) % 4]
        # コード(サイドチェインでポンピング)
        nb = int(BEAT * 4 * SR)
        ch = sum(supersaw(m, nb) for m in notes) / 3
        ch = lp(ch, 3200) * env(nb, 0.01, 10, 1.0, rel=0.03)
        add(L, ch, t0, 0.22); add(R, np.roll(ch, 240), t0, 0.22)
        # ベース(8分刻み・裏拍強め)
        for k in range(8):
            nn = int(BEAT / 2 * SR * 0.9)
            bs = lp(saw(mtof(root - 12), nn) + 0.6 * np.sin(2 * np.pi * mtof(root - 24) * np.arange(nn) / SR), 700)
            bs *= env(nn, 0.004, 0.12, 0.5, rel=0.02)
            add(L, bs, t0 + k * BEAT / 2, 0.30); add(R, bs, t0 + k * BEAT / 2, 0.30)
        if drums:
            for q in range(4):
                tq = t0 + q * BEAT
                add(L, K, tq, 0.55); add(R, K, tq, 0.55)
                i = int(tq * SR); kick_env[i:i + int(0.25 * SR)] = 1
                if q in (1, 3):
                    add(L, C, tq, 0.5); add(R, C, tq + 0.003, 0.5)
                for h in range(2):
                    oh = (h == 1)
                    x = hat(oh)
                    add(L, x, tq + h * BEAT / 2, 0.5 if oh else 0.35); add(R, x, tq + h * BEAT / 2 + 0.004, 0.45)
            if (b + start_bar) % 4 == 3:  # 4小節ごとにフィル
                for k in range(4):
                    add(L, C, t0 + 3 * BEAT + k * s16, 0.25 + 0.1 * k); add(R, C, t0 + 3 * BEAT + k * s16, 0.25 + 0.1 * k)
        if lead:
            ph = ((b + start_bar) % 4) * 16
            for st, ln, m in LEAD:
                if ph <= st < ph + 16:
                    nn = int(ln * s16 * SR)
                    x = pluck(m, nn + int(0.15 * SR)) * 0.6 + bell(m, nn + int(0.15 * SR)) * 0.25
                    tt = t0 + (st - ph) * s16
                    add(L, x, tt, 0.20); add(R, x, tt, 0.20)
                    # ピンポンディレイ(付点8分)
                    add(R, x, tt + BEAT * 0.75, 0.08); add(L, x, tt + BEAT * 1.5, 0.05)
    # サイドチェイン(キック由来)
    sc = np.convolve(kick_env, np.ones(int(0.01 * SR)) / int(0.01 * SR), 'same')
    duck = 1 - 0.55 * sc * 0  # 合成済みドラムも含むため、ダッキングはコード/ベースに近似的に全体へ適用
    pump = np.ones(n)
    for b in range(bars * 4):
        i = int(b * BEAT * SR); m = int(BEAT * SR)
        if drums and i < n:
            seg = 1 - 0.5 * np.exp(-np.arange(min(m, n - i)) / SR / 0.09)
            pump[i:i + len(seg)] = seg
    L *= pump; R *= pump
    return np.stack([L, R])[:, :int(dur * SR)]

def breakdown(dur):
    """ブレイク: パッド(ローパス)+上昇ライザー+加速スネアロール"""
    n = int(dur * SR); t = np.arange(n) / SR
    root, notes = CHORDS[1]  # G でサスペンド感
    pad = sum(supersaw(m, n) for m in notes + [79]) / 4
    cut = 300 + 3500 * (t / dur) ** 2
    # 時間可変ローパスの近似: 数ブロックに分けて処理
    out = np.zeros(n); blk = int(0.05 * SR)
    for i in range(0, n, blk):
        seg = pad[max(0, i - blk): i + blk]
        y = lp(seg, cut[i])
        out[i:i + blk] = y[-len(pad[i:i + blk]):] if i else y[:len(pad[i:i + blk])]
    pad = out * np.minimum(t / 0.3, 1) * 0.3
    riser = hp(rng.standard_normal(n), 1500) * (t / dur) ** 2 * 0.25
    roll = np.zeros(n); C = clap(); tt = 0.0; k = 0
    while tt < dur - 0.05:
        step = BEAT / (1 if tt < dur * 0.4 else 2 if tt < dur * 0.7 else 4)
        add(roll, C, tt, 0.1 + 0.4 * tt / dur); tt += step
    m = pad + riser + roll
    return np.stack([m, m])

# ---------- 効果音 ----------
def sfx_whoosh(d=0.45):
    n = int(d * SR); t = np.arange(n) / SR
    no = rng.standard_normal(n); out = np.zeros(n); blk = int(0.02 * SR)
    for i in range(0, n, blk):
        f = 400 + 5000 * np.sin(np.pi * t[i] / d) ** 2
        out[i:i + blk] = bp(no[i:i + blk], f * 0.6, min(f * 1.6, 20000))
    return out * np.sin(np.pi * t / d) ** 2 * 0.6
def sfx_impact():
    n = int(1.2 * SR); t = np.arange(n) / SR
    f = 35 + 80 * np.exp(-t / 0.08)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.45)
    x += lp(rng.standard_normal(n), 2500) * np.exp(-t / 0.15) * 0.5
    return np.tanh(x * 2) * 0.8
def sfx_pop():
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 500 + 1400 * np.exp(-t / 0.02)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04) * 0.5
def sfx_ding():
    n = int(1.0 * SR)
    return (bell(96, n) * 0.5 + bell(103, n) * 0.3) * 0.5
def sfx_tick():
    n = int(0.03 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.006) * 0.25
def sfx_swell(d):  # 逆再生シンバル風
    n = int(d * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 4000) * (t / d) ** 3 * 0.5

def write(path, x):
    x = np.atleast_2d(x)
    with wave.open(path, 'wb') as w:
        w.setnchannels(x.shape[0]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x.T, -1, 1) * 32767).astype(np.int16).tobytes())
def read(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

if __name__ == '__main__':
    tl = json.load(open(os.path.join(OUT, 'timeline.json')))
    total = tl['total']; N = int(total * SR)
    sc = {s['id']: s for s in tl['scenes']}
    brk = sc['r1']['start']                      # 第1位でブレイク
    drop = sc['r1']['lines'][3]['start']         # 「住所は東京都!!」で再ドロップ
    music = np.zeros((2, N + SR))
    a = section(brk + 0.2); a[:, -int(0.2 * SR):] *= np.linspace(1, 0, int(0.2 * SR))
    music[:, :a.shape[1]] += a
    b = breakdown(drop - brk); music[:, int(brk * SR): int(brk * SR) + b.shape[1]] += b
    c = section(total - drop + 0.5, start_bar=0)
    i = int(drop * SR); m = min(c.shape[1], music.shape[1] - i); music[:, i:i + m] += c[:, :m]
    music = music[:, :N]
    music[:, -int(0.15 * SR):] *= np.linspace(1, 0.6, int(0.15 * SR))  # ループ再生で冒頭へ自然に戻るよう尻は切らない
    music /= np.max(np.abs(music)) / 0.9
    write(os.path.join(OUT, 'bgm.wav'), music)

    # 効果音の配置
    fx = np.zeros(N + 2 * SR)
    W, I, P, D, T = sfx_whoosh(), sfx_impact(), sfx_pop(), sfx_ding(), sfx_tick()
    add(fx, I, 0.0, 0.9)  # 冒頭インパクト
    for s in tl['scenes'][1:]:
        add(fx, W, s['start'] - 0.2, 0.7)
        add(fx, P, s['lines'][0]['start'] + 0.05, 0.8)
    for s in tl['scenes']:
        for l in s['lines'][1:]:
            if '【' in l['text']:
                add(fx, P, l['start'] + 0.08, 0.35)
    # カウントアップ演出のティック → 到達でディング
    for sid, li in (('r5', 1), ('r4', 2), ('r3', 1), ('r2', 3), ('r1', 2)):
        l = sc[sid]['lines'][li]; t0 = l['start'] + 0.1; t1 = t0 + 1.0
        tt = t0
        while tt < t1:
            add(fx, T, tt, 0.6); tt += 0.06
        add(fx, D, t1, 0.55)
    add(fx, sfx_swell(1.5), drop - 1.5, 0.6)
    add(fx, I, drop, 1.0)
    fx = fx[:N]
    write(os.path.join(OUT, 'sfx.wav'), fx)

    # ミックス(ナレーションでBGMをダッキング)
    nar = read(os.path.join(OUT, 'narration.wav'))[:N]
    nar = np.pad(nar, (0, N - len(nar)))
    hop = SR // 50
    rms = np.sqrt(np.mean(nar[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
    e = np.zeros_like(rms)
    for k, v in enumerate(rms): e[k] = max(v, (e[k - 1] if k else 0) * 0.96)
    e = np.pad(np.repeat(e, hop), (0, N - len(rms) * hop))
    sp = np.clip(e / 0.06, 0, 1)
    g = 0.42 - 0.24 * sp
    g = np.convolve(g, np.ones(SR // 20) / (SR // 20), 'same')
    vox = hp(nar, 90)
    mix = music * g + vox[None] * 1.0 + fx[None] * 0.55
    mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    write(os.path.join(OUT, 'mix.wav'), mix)
    print('wrote bgm.wav sfx.wav mix.wav', total)
