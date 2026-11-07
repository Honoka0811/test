# -*- coding: utf-8 -*-
"""アップテンポなポップBGM と効果音を numpy だけで合成する(外部音源不要・権利フリー)。
F メジャー / 124BPM / 進行 F-C-Dm-B♭(王道の I-V-vi-IV)。
  イントロ(フック中): フィルターのかかったコード+ハイハット → 2小節のライザー
  ドロップ(コツ1から): 4つ打ちキック・クラップ・裏拍ベース・サイドチェインのかかったパッド・プラック・リードのモチーフ
  CTA: キックを抜いて落ち着かせ、最後にヒットで締める
効果音はナレーションのタイミング(output/timing.js)に合わせて配置する。
  シーン切り替え=ウーッシュ / コツ番号=インパクト / キーワード=ポップ音 / カレンダー=チェック音 / ✕=ブッ
"""
import json, os
import numpy as np

SR = 48000
BPM = 124
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.abspath(__file__))

def load_timing():
    s = open(os.path.join(HERE, 'output', 'timing.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'): s.rindex('}') + 1])

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
rng = np.random.default_rng(11)

def add(buf, t0, sig, gain=1.0, pan=0.0):
    """buf: (n, 2)。pan -1(左)〜+1(右)"""
    s = int(round(t0 * SR))
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if e <= s: return
    l, r = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    buf[s:e, 0] += sig[:e - s] * gain * l * 1.414
    buf[s:e, 1] += sig[:e - s] * gain * r * 1.414

def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, k):  # 簡易ローパス(移動平均)
    k = max(1, int(k)); return np.convolve(x, np.ones(k) / k, mode='same')
def hp(x, k): return x - lp(x, k)

def saw(f, d, nh=14, det=0.0, ph=0.0):
    t = tt(d); y = np.zeros_like(t)
    for h in range(1, nh + 1):
        if f * h > 9000: break
        y += np.sin(2 * np.pi * f * (1 + det) * h * t + ph * h) / h
    return y * 0.6

# ---------------- 楽器 ----------------
def kick():
    t = tt(.32); f = 45 + 110 * np.exp(-t / .035)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .16)
    y[:200] += rng.standard_normal(200) * np.linspace(.5, 0, 200)
    return np.tanh(y * 1.6)
def clap():
    t = tt(.25); n = rng.standard_normal(len(t))
    env = sum(np.exp(-np.clip(t - o, 0, None) / .008) * (t >= o) for o in (0, .011, .022)) * .5 + np.exp(-t / .09) * (t >= .022)
    return hp(lp(n, 3), 30) * env * .7
def hat(d=.05):
    t = tt(d + .05); return hp(rng.standard_normal(len(t)), 4) * np.exp(-t / d) * .35
def pluck(f, d=.35):
    t = tt(d); y = saw(f, d, nh=10) * np.exp(-t / .09)
    return lp(y, 2)
def bass(f, d):
    t = tt(d); y = saw(f, d, nh=8) + .6 * np.sin(2 * np.pi * f / 2 * t)
    env = np.minimum(1, t / .005) * np.exp(-t / (d * .9))
    return np.tanh(lp(y, 6) * 1.4) * env * .55
def pad(notes, d, bright=1.0):
    t = tt(d); L = np.zeros_like(t); R = np.zeros_like(t)
    for n in notes:
        f = midi(n)
        L += saw(f, d, nh=int(6 + 8 * bright), det=-.006, ph=rng.uniform(0, 6))
        R += saw(f, d, nh=int(6 + 8 * bright), det=+.006, ph=rng.uniform(0, 6))
    env = np.minimum(1, t / .08) * np.minimum(1, (d - t) / .15).clip(0)
    k = 2 if bright > .7 else 10
    return lp(L * env, k) / len(notes), lp(R * env, k) / len(notes)
def lead(f, d):
    t = tt(d); vib = 1 + .006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / .2)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    y = np.sin(ph) + .35 * np.sin(2 * ph) + .2 * np.sign(np.sin(ph)) * .3
    return y * np.minimum(1, t / .01) * np.exp(-t / .5) * .5

# ---------------- 効果音 ----------------
def whoosh(d=.45):
    t = tt(d); n = rng.standard_normal(len(t))
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    y = np.zeros_like(t)
    for i, k in enumerate((40, 20, 10, 5, 3)):   # だんだん明るくなるノイズ
        seg = (t / d >= i / 5) & (t / d < (i + 1) / 5 + .1)
        y += lp(n, k) * seg
    return hp(y, 60) * env * 1.2
def impact():
    t = tt(1.2); f = 30 + 70 * np.exp(-t / .08)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .4)
    crash = hp(rng.standard_normal(len(t)), 3) * np.exp(-t / .35) * .25
    return np.tanh((boom + crash) * 1.5) * .9
def pop(f=900):
    t = tt(.12); ff = f * (1 + 1.5 * np.exp(-t / .015))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t / .04) * .6
def tick(f=2200):
    t = tt(.08); return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 1.5 * t)) * np.exp(-t / .02) * .35
def buzz():
    t = tt(.22); y = np.sign(np.sin(2 * np.pi * 110 * t)) + .5 * np.sign(np.sin(2 * np.pi * 116 * t))
    return lp(y, 8) * np.exp(-t / .1) * .35
def ding(f=1568):
    t = tt(1.0); return sum(np.sin(2 * np.pi * f * h * t) * np.exp(-t / (.5 / h)) / h for h in (1, 2.76, 5.4)) * .4
def riser(d):
    t = tt(d); k = t / d; n = rng.standard_normal(len(t))
    y = np.zeros_like(t)
    for i in range(8):
        seg = (k >= i / 8) & (k < (i + 1) / 8)
        y += lp(n, 24 >> min(i // 2, 4)) * seg
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * k ** 2) / SR) * .25
    return (hp(y, 40) * .8 + tone) * k ** 2

def reverb(x, mix=.22, dl=(1499, 1801, 2213, 2617)):
    def comb(x, d, g):
        y = x.copy()
        for s in range(d, len(y), d):
            e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
        return y
    wet = sum(comb(x, d, .62) for d in dl) / len(dl)
    return (1 - mix) * x + mix * lp(wet, 3)

# ---------------- 曲 ----------------
PROG = [[53, 57, 60], [48, 52, 55, 60], [50, 53, 57], [46, 50, 53]]  # F C Dm Bb
ROOTS = [41, 36, 38, 34]
MOTIF = [(0, 72, .5), (.5, 69, .5), (1, 72, .5), (1.5, 74, 1), (2.5, 72, .5), (3, 69, 1)]   # 拍, MIDI, 長さ(拍)
MOTIF2 = [(0, 72, .5), (.5, 69, .5), (1, 72, .5), (1.5, 77, 1), (2.5, 76, .5), (3, 74, 1)]

def kw_time(c):
    plain = c['text'].replace('【', '').replace('】', ''); i = c['text'].find('【')
    if i < 0: return None
    return c['start'] + (c['end'] - c['start']) * (i / len(plain)) * .92

def ease_io(k):
    k = min(max(k, 0), 1); return 4 * k ** 3 if k < .5 else 1 - (-2 * k + 2) ** 3 / 2

def generate(T):
    total = T['total']; n = int(total * SR) + SR
    sc = {s['id']: s for s in T['scenes']}
    DROP, CTA = sc['tip1']['start'], sc['cta']['start']
    origin = DROP - BAR * np.ceil(DROP / BAR)      # ドロップが小節頭に来るよう拍グリッドを合わせる
    music = {k: np.zeros((n, 2)) for k in ('drums', 'bass', 'pad', 'pluck', 'lead')}
    side = np.ones(n)                              # サイドチェイン用ゲイン
    nbars = int(np.ceil((total - origin) / BAR)) + 1
    for b in range(nbars):
        t0 = origin + b * BAR
        if t0 > total: break
        ci = b % 4; chord = PROG[ci]
        intro, outro_ = t0 + BAR <= DROP + 1e-6, t0 >= CTA - 1e-6
        full = not intro and not outro_
        end_bar = t0 + BAR > total - .2
        # パッド
        L, R = pad([m + 12 for m in chord] + [chord[0]], BAR + .05, bright=.4 if intro else 1)
        g = .16 if intro else .22
        add(music['pad'], t0, L, g, -.6); add(music['pad'], t0, R, g, .6)
        for k in range(4):
            tb = t0 + k * BEAT
            if full:
                add(music['drums'], tb, kick(), .9)
                s = int(tb * SR); m = min(n, s + int(.2 * SR))
                if 0 <= s < n: side[s:m] = np.minimum(side[s:m], 1 - .65 * np.exp(-np.arange(m - s) / SR / .09))
                if k % 2: add(music['drums'], tb, clap(), .55, .1)
                add(music['drums'], tb + BEAT / 2, hat(.12), .35, .3)                     # 裏拍オープンハット
                add(music['bass'], tb + BEAT / 2, bass(midi(ROOTS[ci]), BEAT * .48), .9)  # 裏拍ベース
                add(music['bass'], tb, bass(midi(ROOTS[ci]), BEAT * .3), .5)
            elif outro_ and not end_bar:
                if k % 2: add(music['drums'], tb, clap(), .35, .1)
                add(music['bass'], tb, bass(midi(ROOTS[ci]), BEAT * .9), .55)
            for h in range(4):                                                            # 16分のクローズハット
                if intro and b % 2 == 0 and h % 2: continue
                add(music['drums'], tb + h * BEAT / 4, hat(.03), (.22 if h % 2 == 0 else .14) * (.6 if intro else 1), -.3)
            # プラックのアルペジオ(16分)
            for h in range(4):
                idx = (k * 4 + h) % 8; arp = [0, 1, 2, 1, 2, 0, 2, 1][idx]
                note = chord[arp % len(chord)] + 12 + (12 if idx in (4, 6) else 0)
                add(music['pluck'], tb + h * BEAT / 4, pluck(midi(note)), (.10 if intro else .13) * (1.2 if h == 0 else 1), .35 if h % 2 else -.35)
        # リードのモチーフ(ドロップ後、2小節ごと)
        if full and b % 2 == 0:
            mot = MOTIF if (b // 2) % 2 == 0 else MOTIF2
            for be, m, d in mot:
                add(music['lead'], t0 + be * BEAT, lead(midi(m), d * BEAT * 1.6), .22)
        if end_bar:
            add(music['drums'], t0, impact(), .7)
    # ライザー(ドロップ前 2 小節)
    rs = DROP - 2 * BAR
    add(music['drums'], rs, riser(2 * BAR), .45)
    mix = (music['drums'] + reverb_st(music['pluck'], .3) + reverb_st(music['lead'], .3)
           + (music['bass'] + music['pad']) * side[:, None])
    # 全体の音量カーブ(最後はフェードアウト)
    env = np.ones(n); fo = int(1.2 * SR); e = int(total * SR)
    env[e - fo:e] = np.linspace(1, 0, fo); env[e:] = 0
    mix *= env[:, None]
    return mix[:int(total * SR)] / (np.max(np.abs(mix)) + 1e-9) * .9

def reverb_st(x, mix):
    return np.stack([reverb(x[:, 0], mix, (1499, 1801, 2213, 2617)), reverb(x[:, 1], mix, (1531, 1871, 2251, 2683))], 1)

def sfx(T):
    total = T['total']; n = int(total * SR); buf = np.zeros((n, 2))
    S = T['scenes']; sc = {s['id']: s for s in S}
    add(buf, 0, impact(), .6)                                  # 冒頭のドン
    for s in S[1:]:
        add(buf, s['start'] - .2, whoosh(), .5, .2)
        if s.get('n'): add(buf, s['start'] + .02, impact(), .8)
    for s in S:
        for c in s['chunks']:
            k = kw_time(c)
            if k is not None: add(buf, k, pop(900 + 120 * (hash(c['text']) % 5)), .55)
    hk = sc['hook']['start']
    for i, tm in enumerate([.15, .32]): add(buf, hk + tm, tick(), .5)
    for tm in [.9, 1.05, 1.2, 1.35]: add(buf, hk + tm, buzz(), .55)
    # コツ4: カレンダーのマルが増えるたびにチェック音(だんだん高く)
    t4 = sc['tip4']; a, b = t4['chunks'][1]['start'], t4['end'] - .2; last = 0
    for i in range(int((b - a) * 100)):
        tm = a + i / 100; cnt = int(ease_io((tm - a) / (b - a)) * 26)
        if cnt > last:
            add(buf, tm, tick(1500 + cnt * 40), .35); last = cnt
    # コツ5: ✕ に合わせてブッ
    t5 = sc['tip5']
    c1 = t5['chunks'][1]; add(buf, kw_time(c1) - .1, buzz(), .5)
    c2 = t5['chunks'][2]; k2 = kw_time(c2)
    for tm in (c2['start'] + .35, k2 + .15, k2 + .35): add(buf, tm, buzz(), .5)
    # CTA: 1つ選ばれたらチャイム、最後に保存のチャイム
    cta = sc['cta']; add(buf, kw_time(cta['chunks'][1]) + .1, ding(), .45)
    add(buf, cta['speech_end'] + .1, ding(2093), .35)
    return buf

if __name__ == '__main__':
    import sys, wave
    T = load_timing()
    x = generate(T)
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'bgm.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
