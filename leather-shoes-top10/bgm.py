# -*- coding: utf-8 -*-
"""ランキング動画向けのアップテンポBGMと効果音を numpy だけで合成する(外部音源不要・権利フリー)。
Aマイナー / 124BPM のフューチャーハウス風。キック4つ打ち + クラップ + ハイハット + サイドチェインのかかったベース + コードスタブ + プラックのリード。
timeline.json に合わせて展開する:
  hook/intro … フィルターを開きながら盛り上げ、ランキング開始で「ドロップ」
  各順位      … 切り替わりにウーッシュ、順位の表示にインパクト音
  3位        … 一段階盛り上げる(リードを追加)
  tease      … スネアロール + ライザーのあと無音で溜める
  1位        … 最大のドロップ + シンバル
  outro      … フェードアウト
python3 bgm.py  →  output/bgm.wav, output/sfx.wav
"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
BPM = 124
BEAT = 60 / BPM
rng = np.random.default_rng(11)

# Am - F - C - G (各1小節)
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOTS = [45, 41, 48, 43]
LEAD = [76, 74, 72, 74, 76, 79, 76, 74,  72, 72, 69, 72, 74, 72, 71, 67]  # 8分音符×16 = 2小節


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, t, sig, g=1.0):
    s = int(t * SR)
    if s >= len(buf): return
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf)); buf[s:e] += g * sig[:e - s]


def tt(d): return np.arange(int(d * SR)) / SR


def lp(x, a):  # 1次ローパス(a: 0..1、小さいほど暗い)
    k = max(1, int(1 / max(a, 1e-3)))
    return np.convolve(x, np.ones(k) / k, mode='same').astype(np.float32)


def noise(d): return rng.standard_normal(int(d * SR)).astype(np.float32)


def hp(x, k=8):  # 簡易ハイパス
    return (x - np.convolve(x, np.ones(k) / k, mode='same')).astype(np.float32)


def kick():
    t = tt(0.45); f = 48 + 140 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) + 0.3 * noise(0.45) * np.exp(-t / 0.004)).astype(np.float32)


def clap():
    t = tt(0.3); n = hp(noise(0.3), 12)
    env = sum(np.exp(-np.clip(t - o, 0, None) / 0.008) * (t >= o) for o in (0, 0.011, 0.022)) * 0.5 + np.exp(-t / 0.09)
    return (n * env * 0.6).astype(np.float32)


def hat(open_=False):
    d = 0.22 if open_ else 0.05; t = tt(d)
    return (hp(noise(d), 3) * np.exp(-t / (0.07 if open_ else 0.012))).astype(np.float32)


def saw(f, d, det=(-0.006, 0.0, 0.006)):
    t = tt(d)
    return sum(2 * ((f * (1 + x) * t + rng.random()) % 1) - 1 for x in det).astype(np.float32) / len(det)


def stab(chord, d):
    t = tt(d)
    s = sum(saw(midi(m), d) for m in chord) / len(chord)
    return lp(s, 0.25) * np.exp(-t / 0.18)


def bass(root, d):
    t = tt(d); f = midi(root - 12)
    s = np.sin(2 * np.pi * f * t) + 0.35 * lp(saw(f, d, (0,)), 0.15)
    env = np.minimum(1, t / 0.01) * np.minimum(1, (d - t) / 0.02)
    return (s * env).astype(np.float32)


def pluck(m, d=0.35):
    t = tt(d); f = midi(m)
    s = 0.6 * np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return (lp(s.astype(np.float32), 0.4) * np.exp(-t / 0.12)).astype(np.float32)


def pad(chord, d):
    t = tt(d)
    s = sum(saw(midi(m + 12), d, (-0.01, -0.003, 0.004, 0.011)) for m in chord) / 3
    env = np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.3)
    return lp(s, 0.08) * env


def riser(d):
    t = tt(d); p = t / d
    n = hp(noise(d), 4) * p ** 2
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1400 * p ** 2) / SR) * p ** 3 * 0.3
    return (n * 0.5 + tone).astype(np.float32)


def whoosh(d=0.5):
    t = tt(d); p = t / d
    env = np.sin(np.pi * p) ** 2
    n = noise(d)
    # 前半は明るく後半は暗く
    out = hp(n, 3) * (1 - p) + lp(n, 0.2) * p
    return (out * env * 0.7).astype(np.float32)


def impact():
    t = tt(1.4); f = 35 + 90 * np.exp(-t / 0.06)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.5)
    crack = hp(noise(1.4), 4) * np.exp(-t / 0.05)
    return (boom + 0.4 * crack).astype(np.float32)


def cymbal(d=2.5):
    t = tt(d)
    return (hp(noise(d), 2) * np.exp(-t / 0.7) * 0.5).astype(np.float32)


def tick():
    t = tt(0.06)
    return (np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.01)).astype(np.float32)


def snare():
    t = tt(0.18)
    return (hp(noise(0.18), 6) * np.exp(-t / 0.05) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04)).astype(np.float32)


def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y


def reverb(x, mix):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.6), (1877, 0.58), (2251, 0.55))) / 3
    return (1 - mix) * x + mix * wet


def generate(tl):
    total = tl['total']; S = {s['id']: s for s in tl['scenes']}
    n = int(total * SR) + SR
    drums, bassb, chords, lead, padb, fx = (np.zeros(n, np.float32) for _ in range(6))
    drop = S['r10']['start']; top3 = S['r3']['start']
    tease0, tease1 = S['tease']['start'], S['r1']['start']
    outro = S['outro']['start']
    # 拍のグリッドはランキング開始(ドロップ)に揃える
    first = drop - np.ceil(drop / BEAT) * BEAT
    nb = int((total - first) / BEAT) + 2
    for i in range(nb):
        t = first + i * BEAT
        if t < 0 or t > total: continue
        bar = int(np.floor((t - drop) / (4 * BEAT) + 1e-6)) % 4
        beat = int(round((t - drop) / BEAT)) % 4
        in_tease = tease0 <= t < tease1
        pre = t < drop
        # イントロ: キックは半分、徐々に
        if pre:
            if beat in (0, 2): add(drums, t, kick(), 0.55)
            add(drums, t + BEAT / 2, hat(), 0.12)
            if beat == 0: add(padb, t, pad(CHORDS[bar], 4 * BEAT + 0.3), 0.6)
            continue
        if in_tease:
            continue
        energy = 1.0 if t < top3 else 1.15
        if t >= tease1: energy = 1.3
        if t >= outro: energy = 0.9
        add(drums, t, kick(), 0.9)
        if beat in (1, 3): add(drums, t, clap(), 0.55 * energy)
        add(drums, t + BEAT / 2, hat(True), 0.18 * energy)
        if t >= top3:
            add(drums, t + BEAT / 4, hat(), 0.08); add(drums, t + 3 * BEAT / 4, hat(), 0.08)
        # ベース(8分の裏拍で跳ねる)
        r = ROOTS[bar]
        add(bassb, t + BEAT / 2, bass(r, BEAT / 2 - 0.01), 0.8)
        if beat == 3: add(bassb, t + BEAT * 0.75, bass(r + 12, BEAT / 4 - 0.01), 0.4)
        # コードスタブ(裏拍)
        add(chords, t + BEAT / 2, stab(CHORDS[bar], BEAT / 2), 0.45 * energy)
        if beat == 0: add(padb, t, pad(CHORDS[bar], 4 * BEAT + 0.3), 0.35)
        # リード(3位以降)
        if t >= top3:
            step = (int(round((t - drop) / BEAT)) % 8) * 2
            for k in range(2):
                add(lead, t + k * BEAT / 2, pluck(LEAD[(step + k) % 16]), 0.5 * (1.2 if t >= tease1 else 1))
    # ---- イントロのライザー → ドロップ ----
    add(fx, drop - 2.0, riser(2.0), 0.5)
    # ---- tease: スネアロール + ライザー → 無音 → 1位でインパクト ----
    roll_end = tease1 - 0.55
    d = roll_end - tease0
    k = 0; tcur = tease0
    while tcur < roll_end:
        p = (tcur - tease0) / d
        add(drums, tcur, snare(), 0.25 + 0.5 * p)
        tcur += BEAT / (2 if p < 0.4 else 4 if p < 0.75 else 8)
    add(fx, tease0, riser(d), 0.55)
    # ---- outro は 2 小節かけてフェードアウト(ナレーション後) ----
    mix = (0.95 * drums + 0.7 * bassb + 0.45 * chords + 0.35 * reverb(lead, 0.35) + 0.25 * padb)
    mix = reverb(mix, 0.12)
    env = np.ones(n, np.float32)
    s = int((total - 2.2) * SR); e = int(total * SR)
    env[s:e] = np.linspace(1, 0, e - s); env[e:] = 0
    # ランキング開始前は少し小さめ
    env[:int(drop * SR)] *= np.linspace(0.6, 0.9, int(drop * SR))
    mix = (mix + fx) * env
    mix = mix[:int(total * SR)]
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)


def sfx_track(tl):
    """ダッキングしない効果音(切り替えのウーッシュ、順位表示のインパクト、1位のシンバル)"""
    total = tl['total']; S = {s['id']: s for s in tl['scenes']}
    n = int(total * SR)
    out = np.zeros(n, np.float32)
    add(out, 0.0, impact(), 0.7)           # 冒頭のつかみ
    for s in tl['scenes']:
        if s['id'].startswith('r') and s['id'] != 'r1':
            add(out, s['start'] - 0.25, whoosh(0.5), 0.5)
            add(out, s['start'] + 0.05, impact(), 0.45)
        if s['id'] == 'outro':
            add(out, s['start'] - 0.25, whoosh(0.5), 0.4)
    r1 = S['r1']['start']
    add(out, r1, impact(), 1.0); add(out, r1, cymbal(), 0.6)
    # 価格タグのカウントアップ音(各順位の 1.4 秒後から 0.5 秒)
    for s in tl['scenes']:
        if s['id'].startswith('r'):
            for k in range(6): add(out, s['start'] + 1.4 + k * 0.07, tick(), 0.12)
    return reverb(out, 0.15)[:n]


def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    tl = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))
    write(os.path.join(HERE, 'output', 'bgm.wav'), generate(tl))
    write(os.path.join(HERE, 'output', 'sfx.wav'), sfx_track(tl) * 0.9)
    print('wrote output/bgm.wav, output/sfx.wav')
