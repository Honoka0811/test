# -*- coding: utf-8 -*-
"""BGM(128BPM・Dマイナー・緊張感のある四つ打ち)と効果音を numpy で合成し、ナレーションにダッキングしてミックスする。
外部音源は使わないため権利フリー。
出力: output/bgm.wav, output/sfx.wav, output/mix.wav, output/events.json
使い方: python3 audio.py
"""
import os, json, wave
import numpy as np
from scipy.signal import butter, lfilter, sosfilt
from events import build, LEVELS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
BPM = 128
BEAT = 60.0 / BPM
BAR = BEAT * 4

tl = json.load(open(os.path.join(OUT, 'timeline.json')))
DURATION = tl['duration']
N = int(round(DURATION * SR))
events = build(tl)
json.dump(events, open(os.path.join(OUT, 'events.json'), 'w'), ensure_ascii=False, indent=0)

rng = np.random.default_rng(11)
midi = lambda n: 440.0 * 2 ** ((n - 69) / 12)

def add(buf, t, sig, g=1.0):
    s = int(t * SR)
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * g

def lp(x, fc, order=2): return sosfilt(butter(order, fc / (SR / 2), 'low', output='sos'), x).astype(np.float32)
def hp(x, fc, order=2): return sosfilt(butter(order, fc / (SR / 2), 'high', output='sos'), x).astype(np.float32)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos'), x).astype(np.float32)

def sweep_lp(x, f0, f1, block=1024):
    """カットオフが f0→f1 に動くローパス(ブロック処理)"""
    y = np.zeros_like(x); zi = None
    nb = int(np.ceil(len(x) / block))
    for i in range(nb):
        fc = f0 * (f1 / f0) ** (i / max(1, nb - 1))
        b, a = butter(2, min(fc, SR / 2 - 100) / (SR / 2), 'low')
        if zi is None: zi = np.zeros(max(len(a), len(b)) - 1)
        seg = x[i * block:(i + 1) * block]
        y[i * block:i * block + len(seg)], zi = lfilter(b, a, seg, zi=zi)
    return y.astype(np.float32)

def env_exp(n, tau): return np.exp(-np.arange(n) / SR / tau).astype(np.float32)
def env_ar(n, a, r):
    e = np.ones(n, dtype=np.float32); na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[n - nr:] *= np.linspace(1, 0, nr)
    return e
def sine_sweep(f0, f1, dur, tau):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.06)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)).astype(np.float32)
def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    return (2 * ((f * (1 + detune) * t) % 1.0) - 1).astype(np.float32)

# ---------------- BGM ----------------
# Dm - Bb - Gm - A(各 1 小節)。ベースは 2 オクターブ下。
CHORDS = [[62, 65, 69], [58, 62, 65], [55, 58, 62], [57, 61, 64]]
ROOTS = [38, 34, 31, 33]

def level_at(t):
    for s in tl['scenes']:
        if s['start'] <= t < s['end']: return LEVELS[s['id']]
    return 1.0

def bgm():
    n = N + SR
    kick = np.zeros(n, np.float32); bass = np.zeros(n, np.float32); hat = np.zeros(n, np.float32)
    clap = np.zeros(n, np.float32); pad = np.zeros(n, np.float32); arp = np.zeros(n, np.float32)
    nbars = int(np.ceil(DURATION / BAR)) + 1
    # 強度カーブ(シーン境界で 0.4 秒かけて変化)
    lv = np.array([level_at(i / 100) for i in range(int(n / SR * 100) + 1)], np.float32)
    lv = np.convolve(lv, np.ones(40) / 40, mode='same')
    lvl = np.interp(np.arange(n) / SR, np.arange(len(lv)) / 100, lv).astype(np.float32)
    kick_sig = sine_sweep(160, 48, 0.4, 0.13)
    kick_sig += 0.4 * hp(rng.standard_normal(len(kick_sig)).astype(np.float32), 2000) * env_exp(len(kick_sig), 0.004)
    hat_c = hp(rng.standard_normal(int(0.07 * SR)).astype(np.float32), 7000) * env_exp(int(0.07 * SR), 0.018)
    hat_o = hp(rng.standard_normal(int(0.25 * SR)).astype(np.float32), 6000) * env_exp(int(0.25 * SR), 0.08)
    clap_sig = bp(rng.standard_normal(int(0.3 * SR)).astype(np.float32), 900, 4500) * env_exp(int(0.3 * SR), 0.06)
    for k in range(3):  # 手拍子っぽい三連の立ち上がり
        clap_sig[int(k * 0.011 * SR):] += 0.0
    for b in range(nbars):
        t0 = b * BAR; ch = CHORDS[b % 4]; root = ROOTS[b % 4]
        L = level_at(t0 + 0.2)
        # パッド(デチューンした鋸波 → ローパス)
        dur = BAR + 0.6; m = int(dur * SR)
        sig = sum(saw(midi(c), m, d) for c in ch for d in (-0.006, 0.006)) / 6
        sig += 0.35 * sum(saw(midi(c - 12), m) for c in ch) / 3
        add(pad, t0, lp(sig, 900 + 1800 * L) * env_ar(m, 0.25, 0.6))
        # ベース: 8 分でゲート、ルート(たまに 5 度)
        for e in range(8):
            f = midi(root + (7 if (e == 6 and b % 2 == 1) else 0))
            m2 = int(BEAT / 2 * SR)
            s = saw(f, m2) + 0.5 * np.sin(2 * np.pi * f * np.arange(m2) / SR)
            add(bass, t0 + e * BEAT / 2, lp(s, 260) * env_ar(m2, 0.004, 0.06) * (1.0 if e % 2 == 0 else 0.8))
        # キック: 四つ打ち(強度 0.5 以上)。
        for q in range(4):
            tt = t0 + q * BEAT
            if level_at(tt) >= 0.5: add(kick, tt, kick_sig)
        # ハイハット: 16 分(強度 0.25 以上)、裏拍にアクセント。4 拍目の裏はオープン
        for s16 in range(16):
            tt = t0 + s16 * BEAT / 4
            Ls = level_at(tt)
            if Ls < 0.25: continue
            if Ls < 0.6 and s16 % 2 == 1: continue   # 低強度では 8 分のみ
            vel = 0.9 if s16 % 4 == 2 else (0.45 if s16 % 2 == 0 else 0.6)
            if s16 == 14 and Ls >= 0.7: add(hat, tt, hat_o, 0.6)
            else: add(hat, tt, hat_c, vel)
        # クラップ: 2・4 拍(強度 0.7 以上)
        for q in (1, 3):
            tt = t0 + q * BEAT
            if level_at(tt) >= 0.7: add(clap, tt, clap_sig)
        # アルペジオ(プラック): 16 分で上昇パターン(強度 0.75 以上)
        pat = [0, 1, 2, 1, 0, 2, 1, 2]
        for s16 in range(16):
            tt = t0 + s16 * BEAT / 4
            if level_at(tt) < 0.75: continue
            note = ch[pat[s16 % 8]] + (12 if s16 % 8 >= 4 else 0)
            m3 = int(0.35 * SR); f = midi(note + 12)
            tone = np.sin(2 * np.pi * f * np.arange(m3) / SR) + 0.35 * np.sin(2 * np.pi * 2 * f * np.arange(m3) / SR)
            add(arp, tt, (tone * env_exp(m3, 0.09)).astype(np.float32), 0.5 if s16 % 2 else 0.7)
    # サイドチェイン: キックのたびにベースとパッドをディップ
    sc = np.ones(n, np.float32)
    dip = 1 - 0.75 * np.exp(-np.arange(int(0.32 * SR)) / SR / 0.09)
    for b in range(nbars):
        for q in range(4):
            tt = b * BAR + q * BEAT
            if level_at(tt) >= 0.5:
                s = int(tt * SR); e = min(s + len(dip), n); sc[s:e] = np.minimum(sc[s:e], dip[:e - s])
    # アルペジオにディレイ(付点 8 分)
    d = int(BEAT * 0.75 * SR)
    arp_d = arp.copy(); arp_d[d:] += 0.42 * arp[:-d]; arp_d[2 * d:] += 0.18 * arp[:-2 * d]
    # ライザー(events の riser)
    riser = np.zeros(n, np.float32)
    for e in events:
        if e['kind'] == 'riser':
            dur = e['end'] - e['t']; m = int(dur * SR)
            nz = rng.standard_normal(m).astype(np.float32)
            r = sweep_lp(nz, 300, 9000) * np.linspace(0.05, 1, m) ** 2
            tone = np.sin(2 * np.pi * np.cumsum(np.linspace(220, 880, m)) / SR) * np.linspace(0, 0.5, m)
            add(riser, e['t'], (r + tone).astype(np.float32) * env_ar(m, 0.1, 0.02), 0.7)
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = (0.95 * norm(kick) + 0.55 * norm(bass) * sc + 0.28 * norm(hat) + 0.45 * norm(clap)
           + 0.42 * norm(pad) * sc * (0.55 + 0.45 * lvl) + 0.30 * norm(arp_d) + 0.5 * norm(riser))
    # 緊張→解放: CTA ではパッドを少し明るく(簡易: 高域を足す)
    mix = np.tanh(mix * 1.3) / np.tanh(1.3)
    mix = mix[:N] * env_ar(N, 0.3, 2.5)
    return (norm(mix) * 0.9).astype(np.float32)

# ---------------- SFX ----------------
def sfx_heartbeat():
    out = np.zeros(int(0.45 * SR), np.float32)
    add(out, 0.0, sine_sweep(95, 42, 0.25, 0.07), 1.0)
    add(out, 0.17, sine_sweep(80, 38, 0.22, 0.06), 0.7)
    return lp(out, 180)
def sfx_tick():
    n = int(0.06 * SR)
    return (0.6 * hp(rng.standard_normal(n).astype(np.float32), 3000) * env_exp(n, 0.004)
            + np.sin(2 * np.pi * 1900 * np.arange(n) / SR) * env_exp(n, 0.012)).astype(np.float32)
def sfx_chime(freqs, dur=0.9, tau=0.28, stagger=0.06):
    out = np.zeros(int(dur * SR), np.float32)
    for i, f in enumerate(freqs):
        m = int((dur - i * stagger) * SR)
        tone = (np.sin(2 * np.pi * f * np.arange(m) / SR) + 0.3 * np.sin(2 * np.pi * 2 * f * np.arange(m) / SR)) * env_exp(m, tau)
        add(out, i * stagger, tone.astype(np.float32), 0.6)
    return out
def sfx_impact(f0=140, f1=38, dur=0.5, noise=0.5):
    n = int(dur * SR)
    body = sine_sweep(f0, f1, dur, 0.16)
    nz = lp(rng.standard_normal(n).astype(np.float32), 2500) * env_exp(n, 0.03)
    return (body + noise * nz).astype(np.float32)
def sfx_whoosh(dur=0.45):
    n = int(dur * SR)
    nz = rng.standard_normal(n).astype(np.float32)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return (sweep_lp(hp(nz, 600), 1200, 7000) * e).astype(np.float32)
def sfx_buzz(dur=0.28):
    n = int(dur * SR); t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * 95 * t)) + 0.5 * np.sign(np.sin(2 * np.pi * 142 * t))
    return (lp(sq.astype(np.float32), 1500) * env_ar(n, 0.005, 0.08)).astype(np.float32)
def sfx_alert():
    n = int(0.22 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 740 * t) * (1 + 0.6 * np.sign(np.sin(2 * np.pi * 14 * t))) / 1.6 * env_ar(n, 0.005, 0.1)).astype(np.float32)
def sfx_alarm():
    out = np.zeros(int(0.8 * SR), np.float32)
    for k in range(3):
        n = int(0.13 * SR); t = np.arange(n) / SR
        add(out, k * 0.19, (np.sin(2 * np.pi * (880 if k % 2 == 0 else 660) * t) * env_ar(n, 0.004, 0.05)).astype(np.float32), 0.7)
    return out
def sfx_pop():
    n = int(0.09 * SR); t = np.arange(n) / SR
    f = 500 + 500 * (t / t[-1])
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ar(n, 0.003, 0.05)).astype(np.float32)
def sfx_counter(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * np.cumsum(np.linspace(180, 720, n)) / SR) * np.linspace(0.3, 1, n)
    ticks = np.zeros(n, np.float32)
    k = 0.0
    while k < dur:
        add(ticks, k, sfx_tick(), 0.35); k += 0.09
    return (0.5 * tone * env_ar(n, 0.2, 0.15) + ticks).astype(np.float32)
def sfx_ring(dur):
    out = np.zeros(int(dur * SR), np.float32)
    k = 0.0
    while k < dur - 0.3:
        add(out, k, sfx_tick(), 0.5); k += 0.5
    return out

def sfx():
    out = np.zeros(N, np.float32)
    for e in events:
        k = e['kind']; t = e['t']
        if k == 'heartbeat': add(out, t, sfx_heartbeat(), 1.0)
        elif k == 'tick': add(out, t, sfx_tick(), 0.9)
        elif k == 'correct': add(out, t, sfx_chime([1047, 1319, 1568, 2093]), 0.9)
        elif k == 'wrong': add(out, t, sfx_buzz(), 0.55)
        elif k == 'stamp': add(out, t, sfx_impact(), 1.0)
        elif k == 'slam': add(out, t, sfx_impact(220, 50, 0.45, 0.8), 1.0)
        elif k == 'whoosh': add(out, t - 0.25, sfx_whoosh(), 0.6)
        elif k == 'alert': add(out, t, sfx_alert(), 0.5)
        elif k == 'alarm': add(out, t, sfx_alarm(), 0.6)
        elif k == 'pop': add(out, t, sfx_pop(), 0.7)
        elif k == 'ding': add(out, t, sfx_chime([784, 988, 1175, 1568], 1.4, 0.4), 0.9)
        elif k == 'counter': add(out, t, sfx_counter(e['end'] - t), 0.6)
        elif k == 'ring': add(out, t, sfx_ring(e['end'] - t), 0.6)
        elif k == 'flash': add(out, t, sfx_impact(300, 60, 0.3, 1.0), 0.5)
    return (out / max(1.0, np.max(np.abs(out)) / 0.9)).astype(np.float32)

def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    with wave.open(os.path.join(OUT, 'narration.wav')) as w:
        voice = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
    music = bgm(); fx = sfx()
    write(os.path.join(OUT, 'bgm.wav'), music); write(os.path.join(OUT, 'sfx.wav'), fx)
    # ダッキング: ナレーションの包絡で BGM を下げる
    hop = SR // 20
    rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(rms)
    for i, v in enumerate(rms):
        env[i] = max(v, (env[i - 1] if i else 0) * 0.88)
    env = np.pad(np.repeat(env, hop), (0, N - len(rms) * hop))
    speech = np.clip(env / 0.10, 0, 1)
    BGM_SILENT, BGM_SPEECH = 0.42, 0.20
    gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
    gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
    mixed = voice * 0.95 + music * gain + fx * 0.85
    mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
    write(os.path.join(OUT, 'mix.wav'), mixed)
    print(f'wrote bgm.wav sfx.wav mix.wav ({N / SR:.1f}s), events.json ({len(events)} events)')
