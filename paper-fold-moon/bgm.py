# -*- coding: utf-8 -*-
"""BGM と効果音をプログラムで合成し(外部音源なし・権利フリー)、ナレーションとミックスする。
入力: output/timeline.json, output/events.json(capture.js が出力), output/narration.wav
出力: output/bgm_sfx.wav(BGM+効果音), output/mix.wav(最終ミックス, ステレオ 48kHz)

BGM: Aマイナー / 120BPM。Am-F-C-G のプラック・アルペジオ + サブベース + パッド。
セクションごとに編成を変える:
  hook/doubt  … パッド + アルペジオ(謎めいた導入)
  f10〜f42    … キック・ハイハット・クラップが段階的に加わり、42回目でライザー → 衝撃音 → 一瞬の無音
  half/last   … ハーフタイム(余韻)
  life/lazy   … フル編成で再び前進
  quit        … ピアノ風の単音とパッドだけ(感情的に)
  ask         … 終止和音でふわっと終わる
"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
BPM = 120
BEAT = 60 / BPM
rng = np.random.default_rng(7)

PROG = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
ROOT = [45, 41, 48, 43]


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)


def tvec(d): return np.arange(int(d * SR)) / SR


def add(buf, t0, sig, gain=1.0, pan=0.0):
    s = int(t0 * SR)
    if s >= buf.shape[0] or s + len(sig) <= 0: return
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), buf.shape[0])
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[s:e, 0] += sig[:e - s] * gain * l * 1.414
    buf[s:e, 1] += sig[:e - s] * gain * r * 1.414


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y


def onepole_fft(x, fc):  # 長い信号用の高速ローパス(周波数領域)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 2), len(x))


# ---------- 楽器 ----------
def pluck(f, d=0.45, bright=1.0):
    t = tvec(d)
    sig = sum((0.6 / h) * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (6 + 5 * h / bright)) for h in range(1, 7))
    return sig * np.minimum(1, t * 400)


def pad(freqs, d):
    t = tvec(d)
    sig = np.zeros_like(t)
    for f in freqs:
        for det in (-0.006, 0, 0.006):
            ph = rng.uniform(0, 6.28)
            sig += sum((1 / h ** 1.6) * np.sin(2 * np.pi * f * (1 + det) * h * t + ph * h) for h in range(1, 5))
    env = np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.6)
    return sig * env / (len(freqs) * 3)


def sub(f, d):
    t = tvec(d)
    return np.sin(2 * np.pi * f * t) * np.minimum(1, t * 50) * np.minimum(1, (d - t) * 30)


def kick():
    t = tvec(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) + 0.3 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 300)


def hat():
    t = tvec(0.06)
    n = rng.standard_normal(len(t)); n = n - lowpass(n, 6000)
    return n * np.exp(-t * 70)


def clap():
    t = tvec(0.25)
    n = rng.standard_normal(len(t)); n = n - lowpass(n, 900)
    env = np.exp(-t * 18) * (1 + 0.6 * ((t % 0.012) < 0.004) * (t < 0.03))
    return n * env * 0.6


def piano(f, d=2.2):
    t = tvec(d)
    sig = sum((0.7 / h ** 1.3) * np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * t) * np.exp(-t * (1.6 + 0.9 * h)) for h in range(1, 8))
    return sig * np.minimum(1, t * 300)


# ---------- 効果音 ----------
def sfx_whoosh(d=0.45):
    t = tvec(d); n = rng.standard_normal(len(t))
    lo = onepole_fft(n, 2500); hi = n - onepole_fft(n, 400)
    env = np.sin(np.pi * t / d) ** 2
    return (lo * 0.5 + hi * 0.5) * env * 0.5


def sfx_tick(n):
    t = tvec(0.09); f = 700 * 2 ** (n / 24)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 55) * 0.5


def sfx_pop(n=0):
    t = tvec(0.16); f = 420 * 2 ** (n / 6) + 600 * np.exp(-t * 40)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 22) * 0.6


def sfx_ding():
    t = tvec(1.2)
    return sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * k) for f, a, k in
               [(1568, 0.5, 4), (2349, 0.3, 6), (3136, 0.15, 9)]) * 0.45


def sfx_hit():
    t = tvec(0.6)
    f = 60 + 200 * np.exp(-t * 20)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    n = rng.standard_normal(len(t)) * np.exp(-t * 25) * 0.4
    return (body + n) * 0.8


def sfx_impact(big=False):
    d = 2.5 if big else 1.4
    t = tvec(d)
    f = 38 + 140 * np.exp(-t * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (1.8 if big else 3.5))
    n = rng.standard_normal(len(t)); n = onepole_fft(n, 3000) * np.exp(-t * 6)
    return (boom * 1.0 + n * 0.8) * (1.0 if big else 0.75)


def sfx_stamp():
    t = tvec(0.35)
    n = onepole_fft(rng.standard_normal(len(t)), 1500) * np.exp(-t * 30)
    return (n * 1.4 + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 18)) * 0.8


def sfx_down():
    t = tvec(1.0); f = 600 * np.exp(-t * 2.2)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.5) * 0.35


def sfx_riser(d):
    t = tvec(d)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(t); seg = int(0.05 * SR)
    for i in range(0, len(t), seg):  # 区間ごとにカットオフを上げるノイズスイープ
        k = i / len(t); fc = 300 * 40 ** k
        out[i:i + seg] = n[i:i + seg] - onepole_fft(n[i:i + seg], fc) if fc < 20000 else n[i:i + seg]
    tone = np.sin(2 * np.pi * np.cumsum(200 * 4 ** (t / d)) / SR)
    return (out * 0.35 + tone * 0.25) * (t / d) ** 2


# ---------- 組み立て ----------
def main():
    tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
    ev = json.load(open(os.path.join(OUT, 'events.json'), encoding='utf-8'))
    L = {l['id']: l for l in tl['lines']}
    total = tl['total']
    S = lambda i: L[i]['start']
    E = lambda i: L[i]['start'] + L[i]['dur']
    hit42 = next(e['t'] for e in ev if e['type'] == 'impact' and e.get('big'))

    def section(t):
        if t < S('f10') - 0.2: return 'intro'
        if hit42 - 0.02 <= t < hit42 + 0.9: return 'drop'
        if t < hit42: return 'build'
        if t < S('life') - 0.2: return 'half'
        if t < S('quit') - 0.2: return 'drive'
        if t < S('ask') - 0.2: return 'emo'
        return 'outro'

    mus = np.zeros((int((total + 3) * SR), 2))
    nb = int(total / BEAT) + 1
    for b in range(nb):
        t = b * BEAT
        sec = section(t)
        bar = b // 4; ch = bar % 4
        chord, root = PROG[ch], ROOT[ch]
        if b % 4 == 0 and sec not in ('drop',):
            g = {'intro': 0.5, 'build': 0.45, 'half': 0.55, 'drive': 0.45, 'emo': 0.6, 'outro': 0.6}[sec]
            add(mus, t, pad([midi(n) for n in chord], BEAT * 4 + 0.6), g * 0.5, 0)
        if sec == 'drop': continue
        # 16分のアルペジオ
        if sec in ('intro', 'build', 'drive', 'half'):
            pat = [0, 1, 2, 1, 0, 2, 1, 2] if sec != 'half' else [0, 2]
            step = BEAT / 4 if sec != 'half' else BEAT
            for k in range(int(BEAT / step)):
                idx = (b * int(BEAT / step) + k) % len(pat)
                n = chord[pat[idx]] + 12
                add(mus, t + k * step, pluck(midi(n), bright=1.5 if sec == 'drive' else 1.0), 0.16, 0.35 if k % 2 else -0.35)
        # ベース
        if sec in ('build', 'drive'):
            for k in (0, 0.5):
                add(mus, t + k * BEAT, sub(midi(root - 12), BEAT * 0.45), 0.35)
        # ドラム: build は段階的に増える
        lvl = 0
        if sec == 'build':
            lvl = 1 if t < S('f20') else 2 if t < S('f42') else 3
        elif sec == 'drive':
            lvl = 3
        if lvl >= 1: add(mus, t, kick(), 0.55)
        if lvl >= 2: add(mus, t + BEAT / 2, hat(), 0.25, 0.3)
        if lvl >= 3:
            add(mus, t + BEAT / 4, hat(), 0.12, -0.3)
            if b % 2 == 1: add(mus, t, clap(), 0.35)
        if sec == 'half' and b % 4 == 0: add(mus, t, kick(), 0.35)
        if sec == 'emo' and b % 2 == 0:
            for j, n in enumerate([chord[2] + 12, chord[1] + 12]):
                add(mus, t + j * BEAT, piano(midi(n)), 0.22, 0.2 * (-1) ** j)
    # 終止和音(Am add9)
    add(mus, S('ask') + 0.2, pad([midi(n) for n in (45, 57, 60, 64, 71)], total - S('ask') + 1.0), 0.45)
    for j, n in enumerate([69, 72, 76, 81]):
        add(mus, S("ask") + 1.0 + j * 0.18, piano(midi(n), 2.5), 0.18)

    # 簡易リバーブ(指数減衰ノイズとの畳み込み)
    ir_t = tvec(1.6)
    rev = np.zeros_like(mus)
    for c in range(2):
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2); ir[0] = 0
        n = len(mus) + len(ir)
        rev[:, c] = np.fft.irfft(np.fft.rfft(mus[:, c], n) * np.fft.rfft(ir, n), n)[:len(mus)]
    mus = mus + rev / np.abs(rev).max() * np.abs(mus).max() * 0.25

    # 効果音
    fx = np.zeros_like(mus)
    for e in ev:
        ty, t = e['type'], e['t']
        if ty == 'whoosh': add(fx, t - 0.2, sfx_whoosh(), 0.5)
        elif ty == 'tick': add(fx, t, sfx_tick(e.get('n', 0)), 0.45, 0.2)
        elif ty == 'pop': add(fx, t, sfx_pop(e.get('n', 0)), 0.55)
        elif ty == 'ding': add(fx, t, sfx_ding(), 0.5)
        elif ty == 'hit': add(fx, t, sfx_hit(), 0.8)
        elif ty == 'impact': add(fx, t, sfx_impact(e.get('big', False)), 1.0)
        elif ty == 'stamp': add(fx, t, sfx_stamp(), 0.9)
        elif ty == 'down': add(fx, t, sfx_down(), 0.6)
        elif ty == 'riser': add(fx, t, sfx_riser(e['until'] - t), 0.55)

    # ナレーションに合わせたダッキング(BGMのみ)
    with wave.open(os.path.join(OUT, 'narration.wav')) as w:
        nar = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    nar = np.pad(nar, (0, len(mus) - len(nar)))
    hop = int(0.02 * SR)
    rms = np.sqrt(np.convolve(nar ** 2, np.ones(hop) / hop, 'same'))
    speaking = (rms > 0.01).astype(float)
    duck = 1 - 0.5 * onepole_fft(speaking, 3)  # 発話中は約 -6dB
    duck = np.clip(duck, 0.45, 1.0)
    mus = mus / np.abs(mus).max() * 0.5 * duck[:, None]
    fx = fx / np.abs(fx).max() * 0.6

    bed = (mus + fx)[:int(total * SR)]
    fade = int(0.4 * SR); bed[-fade:] *= np.linspace(1, 0, fade)[:, None]
    # BGM+効果音の平均音量を、ナレーション(発話部分)より約 9dB 下にそろえる
    nv = nar[:len(bed)]
    nar_rms = np.sqrt((nv[np.abs(nv) > 0.02] ** 2).mean())
    bed = bed * (nar_rms * 10 ** (-9 / 20) / np.sqrt((bed ** 2).mean()))
    mix = bed + nv[:, None]
    mix = mix / np.abs(mix).max() * 0.95

    def save(name, x):
        with wave.open(os.path.join(OUT, name), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    save('bgm_sfx.wav', bed / np.abs(bed).max() * 0.9)
    save('mix.wav', mix)
    print('ok', len(mix) / SR, 's')


if __name__ == '__main__':
    main()
