# -*- coding: utf-8 -*-
"""ポップ系BGM と 効果音 をプログラムで合成する(外部音源不要・権利フリー)。
- BGM: 120BPM / ハ長調 / 王道進行(F→G→Em→Am)。4つ打ちキック・クラップ・裏拍ハイハット・
       ベース・サイドチェインのかかったパッド・16分のアルペジオ・リードのフック。
       タイムラインに合わせて「イントロ→ドロップ→TOP3前のビルド→1位発表前のブレイク→再ドロップ→アウトロ」と展開する。
- 効果音: whoosh / impact / impact_big / drumroll / reveal
すべてステレオ (2, n) の float32 で返す。
"""
import numpy as np
from scipy import signal

SR = 48000

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, t, sig, pan=0.0):
    """buf: (2, n)。sig: mono(n,) または (2, n)。pan -1..1"""
    s = int(round(t * SR))
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.414, sig * r * 1.414])
    if s < 0: sig = sig[:, -s:]; s = 0
    e = min(s + sig.shape[1], buf.shape[1])
    if e > s: buf[:, s:e] += sig[:, :e - s]

def lp(x, fc, order=2):
    b, a = signal.butter(order, min(fc / (SR / 2), 0.99), 'low'); return signal.lfilter(b, a, x, axis=-1).astype(np.float32)
def hp(x, fc, order=2):
    b, a = signal.butter(order, min(fc / (SR / 2), 0.99), 'high'); return signal.lfilter(b, a, x, axis=-1).astype(np.float32)
def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], 'band'); return signal.lfilter(b, a, x, axis=-1).astype(np.float32)

def env(n, a=0.005, d=0.2, s=0.0, r=0.05, hold=None):
    """ADSR(hold = 鍵盤を押している時間)"""
    t = np.arange(n) / SR
    hold = hold if hold is not None else n / SR
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = t > hold
    e[rel] *= np.exp(-(t[rel] - hold) / max(r, 1e-6))
    return e.astype(np.float32)

def saw(f, n, harm=14, phase=0.0):
    t = np.arange(n) / SR; x = np.zeros(n, np.float32)
    for h in range(1, harm + 1):
        if f * h > 16000: break
        x += np.sin(2 * np.pi * f * h * t + phase * h) / h
    return x * 0.55

rng_global = np.random.default_rng(3)
def noise(n, rng=None):
    return (rng or rng_global).standard_normal(n).astype(np.float32)

# ---------------- 楽器 ----------------
def kick(n=int(0.35 * SR)):
    t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    x += 0.35 * lp(noise(n), 3000) * np.exp(-t / 0.004)
    return np.tanh(1.6 * x).astype(np.float32) * 0.9

def clap(n=int(0.3 * SR)):
    t = np.arange(n) / SR
    e = np.zeros(n, np.float32)
    for k, d in enumerate((0, 0.011, 0.022)):
        m = t >= d; e[m] += np.exp(-(t[m] - d) / (0.006 if k < 2 else 0.09))
    return bp(noise(n), 900, 5000) * e * 0.7

def hat(n=int(0.07 * SR), open_=False):
    if open_: n = int(0.25 * SR)
    t = np.arange(n) / SR
    return hp(noise(n), 7000) * np.exp(-t / (0.08 if open_ else 0.018)) * 0.45

def snare(n=int(0.2 * SR)):
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    return (0.5 * body + bp(noise(n), 1500, 8000) * np.exp(-t / 0.07)).astype(np.float32) * 0.6

def bass_note(f, dur):
    n = int((dur + 0.05) * SR)
    x = saw(f, n, harm=10) + 0.6 * np.sin(2 * np.pi * f / 2 * np.arange(n) / SR)
    x = lp(x, 900)
    return (np.tanh(1.3 * x) * env(n, 0.004, 0.25, 0.6, 0.03, hold=dur)).astype(np.float32)

def pluck(f, dur=0.22):
    n = int((dur + 0.25) * SR)
    x = saw(f, n, harm=8) + 0.5 * np.sin(2 * np.pi * 2 * f * np.arange(n) / SR)
    return lp(x, 4200) * env(n, 0.002, 0.11, 0.0, 0.05)

def bell(f, dur=0.5):
    n = int((dur + 0.6) * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t / 0.15))
    return (x * env(n, 0.002, 0.35, 0.0, 0.2)).astype(np.float32)

def lead(f, dur):
    n = int((dur + 0.15) * SR); t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.12) / 0.2, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    x = np.sign(np.sin(ph)) * 0.35 + np.sin(ph) * 0.5 + 0.25 * np.sin(2 * ph)
    x = lp(x, 3200)
    return (x * env(n, 0.01, 0.4, 0.75, 0.08, hold=dur)).astype(np.float32)

def pad_chord(notes, dur):
    n = int((dur + 0.3) * SR)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)
    for m in notes:
        f = midi(m)
        for det, side in ((-0.006, 0), (0.0, 2), (0.006, 1)):
            x = saw(f * (1 + det), n, harm=10, phase=rng_global.uniform(0, 6.28))
            if side in (0, 2): L += x
            if side in (1, 2): R += x
    e = env(n, 0.05, 1.0, 0.8, 0.25, hold=dur)
    return np.stack([lp(L, 2600), lp(R, 2600)]) * e / (len(notes) * 2)

# ---------------- 曲 ----------------
BPM = 120; BEAT = 60 / BPM; BAR = 4 * BEAT
CHORDS = [  # 王道進行(F△7 → G → Em7 → Am)
    dict(root=41, notes=[53, 57, 60, 64]),
    dict(root=43, notes=[55, 59, 62, 67]),
    dict(root=40, notes=[52, 55, 59, 62]),
    dict(root=45, notes=[57, 60, 64, 69]),
]
# リードのフック(拍, MIDI, 長さ[拍]) 4小節
HOOK = [(0, 76, 1), (1, 74, .5), (1.5, 72, .5), (2, 72, 1), (3, 69, 1),
        (4, 71, .5), (4.5, 72, .5), (5, 74, 1), (6, 79, 1.5), (7.5, 76, .5),
        (8, 76, 1), (9, 74, .5), (9.5, 76, .5), (10, 79, 1), (11, 71, 1),
        (12, 72, 1), (13, 71, .5), (13.5, 69, .5), (14, 69, 2)]

def section_at(t, S):
    for name, a, b in S:
        if a <= t < b: return name
    return None

def generate(tl):
    total = tl['duration']
    n = int((total + 1) * SR)
    sc = {s['id']: s for s in tl['scenes']}
    drop1 = sc['r10']['a']; top3 = sc['top3']['a']; drop2 = sc['r3']['a']
    brk = sc['build']['a']; reveal = tl['reveal']; end_a = sc['end']['a']
    S = [('intro', 0, drop1), ('main', drop1, top3), ('build', top3, drop2), ('main2', drop2, brk),
         ('break', brk, reveal), ('final', reveal, end_a), ('outro', end_a, total + 1)]

    drums = np.zeros((2, n), np.float32); bass = np.zeros((2, n), np.float32)
    pads = np.zeros((2, n), np.float32); arps = np.zeros((2, n), np.float32)
    leads = np.zeros((2, n), np.float32); fx = np.zeros((2, n), np.float32)
    duck = np.ones(n, np.float32)  # サイドチェイン
    K = kick(); C = clap(); H = hat(); HO = hat(open_=True)

    nbeats = int(total / BEAT) + 2
    for i in range(nbeats):
        t = i * BEAT
        sec = section_at(t, S)
        bar = int(t // BAR); beat_in_bar = i % 4
        ch = CHORDS[bar % 4]
        if sec in ('main', 'main2', 'final', 'outro', 'build'):
            fade = 1.0
            if sec == 'outro': fade = max(0.0, 1 - (t - end_a) / max(total - end_a, 0.1))
            if sec == 'build':  # TOP3 前: キック4分→8分のスネアロールで盛り上げ
                add(drums, t, K * 0.9)
                for k in range(4 if t > drop2 - BAR else 2):
                    add(drums, t + k * BEAT / (4 if t > drop2 - BAR else 2), snare() * (0.3 + 0.6 * (t - top3) / max(drop2 - top3, 0.1)))
            else:
                add(drums, t, K * fade)
                s = int(t * SR); m = int(0.22 * SR)
                if s + m < n: duck[s:s + m] = np.minimum(duck[s:s + m], 0.35 + 0.65 * np.linspace(0, 1, m) ** 0.7)
                if beat_in_bar in (1, 3): add(drums, t, C * fade, 0.0)
                add(drums, t + BEAT / 2, (HO if beat_in_bar == 3 else H) * fade, 0.3)
                add(drums, t + BEAT / 4, H * 0.35 * fade, -0.3)
                add(drums, t + 3 * BEAT / 4, H * 0.35 * fade, -0.3)
        elif sec == 'intro':
            # イントロ: 裏拍のハイハットとクラップだけで軽く
            add(drums, t + BEAT / 2, H * 0.7, 0.3)
            if beat_in_bar == 3 and t > 2: add(drums, t, C * 0.6)
        # ベース(8分、ルートとオクターブ)
        if sec in ('main', 'main2', 'final', 'outro', 'build'):
            fade = 1.0 if sec != 'outro' else max(0.0, 1 - (t - end_a) / max(total - end_a, 0.1))
            for k in range(2):
                m = ch['root'] + (12 if k == 1 else 0)
                add(bass, t + k * BEAT / 2, bass_note(midi(m), BEAT / 2 * 0.85) * 0.55 * fade)
        # アルペジオ(16分)
        if sec in ('intro', 'main', 'main2', 'final', 'outro', 'build'):
            vol = 0.22 if sec == 'intro' else 0.3
            if sec == 'outro': vol *= max(0.0, 1 - (t - end_a) / max(total - end_a, 0.1))
            order = [0, 1, 2, 3, 2, 1, 3, 2]
            for k in range(4):
                idx = order[(beat_in_bar * 4 + k) % 8]
                add(arps, t + k * BEAT / 4, pluck(midi(ch['notes'][idx] + 12)) * vol, 0.45 if k % 2 else -0.45)
        # パッド(小節頭)
        if beat_in_bar == 0 and sec not in ('break',):
            vol = 0.5 if sec == 'intro' else 0.8
            dur = BAR
            if t + BAR > brk and t < brk: dur = brk - t
            add(pads, t, pad_chord(ch['notes'], dur) * vol)

    # リード: ドロップ直後の4小節と、1位発表後〜アウトロ
    def place_hook(t0, vol=0.22, octave=0):
        for b, m, L in HOOK:
            tt = t0 + b * BEAT
            if tt >= brk and t0 < brk: break
            add(leads, tt, lead(midi(m + octave), L * BEAT * 0.92) * vol, 0.1)
            add(leads, tt + 0.375, lead(midi(m + octave), L * BEAT * 0.92) * vol * 0.3, -0.6)  # ディレイ
    first_bar = lambda t: np.ceil(t / BAR - 1e-6) * BAR
    place_hook(first_bar(drop1))
    place_hook(first_bar(drop2), 0.2)
    t = first_bar(reveal)
    while t + 4 * BAR <= total + 0.01:
        place_hook(t, 0.24); t += 4 * BAR
    # イントロのベル(フックの予告)
    for b, m, L in HOOK[:10]:
        if b * BEAT + BAR < drop1 - BAR:
            add(leads, BAR + b * BEAT, bell(midi(m), L * BEAT) * 0.18, 0.2)

    # ライザー(ドロップ前 1小節 / TOP3 ビルド全体)
    def riser(t0, t1, vol=0.35):
        L = int((t1 - t0) * SR)
        if L <= 0: return
        x = noise(L); p = np.linspace(0, 1, L)
        out = np.zeros(L, np.float32); blk = 2400
        for s in range(0, L, blk):
            fc = 400 + 7000 * p[s] ** 2
            out[s:s + blk] = bp(x[s:s + blk + 0], fc * 0.7, fc * 1.3, 1)[:len(out[s:s + blk])]
        add(fx, t0, out * p ** 1.5 * vol)
    riser(drop1 - BAR, drop1)
    riser(top3, drop2, 0.3)

    music = (0.9 * drums + 0.8 * bass + 0.55 * pads * duck + 0.6 * arps * duck + 0.8 * leads + fx)
    # 全体の明るさ: イントロ冒頭は少しローパスから開く
    m = int(min(drop1, 4.0) * SR)
    music[:, :m] = music[:, :m] * np.linspace(0.6, 1.0, m)
    music *= env_edges(music.shape[1], 0.05, 1.5, total)
    music = np.tanh(music * 1.1) / 1.1
    return music[:, :int(total * SR)].astype(np.float32)

def env_edges(n, fin, fout, total):
    e = np.ones(n, np.float32); t = np.arange(n) / SR
    e *= np.clip(t / fin, 0, 1); e *= np.clip((total - t) / fout, 0, 1)
    return e

# ---------------- 効果音 ----------------
def sfx_whoosh(dur=0.45):
    L = int(dur * SR); p = np.linspace(0, 1, L)
    x = noise(L); out = np.zeros(L, np.float32); blk = 1200
    for s in range(0, L, blk):
        fc = 600 + 5000 * np.sin(np.pi * p[s]) ** 2
        out[s:s + blk] = bp(x[s:s + blk], fc * 0.6, fc * 1.4, 1)[:len(out[s:s + blk])]
    e = np.sin(np.pi * p) ** 2
    pan = np.linspace(-0.8, 0.8, L)
    return np.stack([out * e * np.cos((pan + 1) * np.pi / 4), out * e * np.sin((pan + 1) * np.pi / 4)]) * 1.0

def sfx_impact(big=False):
    L = int((1.4 if big else 0.8) * SR); t = np.arange(L) / SR
    f = 38 + (120 if big else 90) * np.exp(-t / 0.06)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.5 if big else 0.25))
    crack = lp(noise(L), 6000) * np.exp(-t / (0.08 if big else 0.03))
    x = np.tanh(1.8 * (boom + 0.5 * crack)) * 0.8
    if big:
        x += hp(noise(L), 5000) * np.exp(-t / 0.6) * 0.25  # シンバル
    return x.astype(np.float32)

def sfx_drumroll(dur):
    L = int((dur + 0.3) * SR); out = np.zeros(L, np.float32)
    t = 0.0; S = snare()
    while t < dur:
        p = t / dur
        g = 0.25 + 0.75 * p ** 1.3
        s = int(t * SR); e = min(s + len(S), L)
        out[s:e] += S[:e - s] * g * np.random.default_rng(int(t * 1000)).uniform(0.8, 1.0)
        t += 0.075 - 0.035 * p      # 加速
    tt = np.arange(L) / SR
    out += np.sin(2 * np.pi * (55 + 30 * tt / dur) * tt) * 0.25 * np.clip(tt / dur, 0, 1)  # 低い唸り
    return out

def sfx_reveal():
    L = int(2.5 * SR); t = np.arange(L) / SR
    x = sfx_impact(big=True)
    out = np.zeros(L, np.float32); out[:len(x)] += x
    out += hp(noise(L), 4000) * np.exp(-t / 0.9) * 0.35  # クラッシュ
    for k, m in enumerate([72, 76, 79, 84, 88]):           # キラキラ上昇アルペジオ
        b = bell(midi(m), 0.4) * 0.22; s = int((0.05 + k * 0.06) * SR)
        e = min(s + len(b), L); out[s:e] += b[:e - s]
    return out

def render_sfx(tl):
    total = tl['duration']
    buf = np.zeros((2, int((total + 3) * SR)), np.float32)
    for e in tl['sfx']:
        ty = e['type']
        if ty == 'whoosh': add(buf, e['t'], sfx_whoosh() * 0.4)
        elif ty == 'impact': add(buf, e['t'], sfx_impact() * 0.42)
        elif ty == 'impact_big': add(buf, e['t'], sfx_impact(True) * 0.5)
        elif ty == 'drumroll': add(buf, e['t'], sfx_drumroll(e['dur']) * 0.6)
        elif ty == 'reveal': add(buf, e['t'], sfx_reveal() * 0.42)
    return buf[:, :int(total * SR)]

if __name__ == '__main__':
    import json, sys, wave, os
    here = os.path.dirname(os.path.abspath(__file__))
    tl = json.load(open(os.path.join(here, 'output', 'timeline.json'), encoding='utf-8'))
    m = generate(tl)
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, 'output', 'bgm.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(m.T, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', out)
