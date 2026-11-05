# -*- coding: utf-8 -*-
"""視聴者を引き込むショート向けBGMを numpy だけで合成する(外部音源なし・権利フリー)。
124BPM のエレクトロ・ポップ。映像のシーン構成(output/sync.json)に合わせて展開を変える。
  フック〜幹線     : 4つ打ち + サイドチェイン・パッド + 16分アルペジオ(Am-F-C-G)で一気に引き込む
  消えた路線       : ドラムを抜いてノスタルジックに
  青函トンネル     : ライザーで溜めて「本州とつながる」で再びフルビート
  廃止ラッシュ     : 暗い進行(Am-Am-F-E)+ハーフタイム。廃止の瞬間ごとに低音インパクト
  比較             : ブレイク →「約3分の1」でドン
  エンディング     : 明るい進行でフルビート、最後にヒット
単体実行: python3 bgm.py [出力wav]
"""
import sys, os, json, wave
import numpy as np

SR = 48000
BPM = 124
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(11)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

BRIGHT = [([57, 60, 64], 45), ([53, 57, 60], 41), ([48, 52, 55, 60], 48), ([55, 59, 62], 43)]   # Am F C G
DARK = [([57, 60, 64], 45), ([57, 60, 64], 45), ([53, 57, 60], 41), ([52, 56, 59], 40)]         # Am Am F E

def add(buf, t, sig, gain=1.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(sig) <= 0: return
    if i < 0: sig = sig[-i:]; i = 0
    e = min(len(buf), i + len(sig)); buf[i:e] += sig[:e - i] * gain

def env(n, a, r, hold=None):
    e = np.ones(n, np.float32)
    na = max(1, min(n, int(a * SR))); nr = max(1, min(n, int(r * SR)))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr)
    return e

def saw(f, n, harm=14, det=0.0, ph=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for h in range(1, harm + 1):
        if f * h > 9000: break
        out += np.sin(2 * np.pi * f * (1 + det) * h * t + ph * h) / h
    return out

def kick(n=int(0.32 * SR)):
    t = np.arange(n) / SR
    f = 46 + 120 * np.exp(-t / 0.035)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    s += 0.25 * np.tanh(rng.standard_normal(n) * np.exp(-t / 0.004))
    return np.tanh(1.6 * s).astype(np.float32)

def hat(n=int(0.06 * SR), dec=0.018):
    x = rng.standard_normal(n).astype(np.float32)
    x = np.diff(np.concatenate([[0], x]))        # 高域を強調
    return x * np.exp(-np.arange(n) / SR / dec)

def clap(n=int(0.25 * SR)):
    t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(12) / 12, 'same')
    e = sum(np.exp(-np.clip(t - d, 0, None) / 0.008) * (t >= d) for d in (0, 0.011, 0.022)) + 0.6 * np.exp(-t / 0.09)
    return (x * e * 0.6).astype(np.float32)

def tom(f0=110, n=int(0.6 * SR)):
    t = np.arange(n) / SR
    f = f0 * (0.55 + 0.45 * np.exp(-t / 0.08))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22)).astype(np.float32)

def impact(n=int(2.4 * SR)):
    t = np.arange(n) / SR
    f = 28 + 70 * np.exp(-t / 0.12)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    noise = rng.standard_normal(n).astype(np.float32)
    crash = (noise - np.convolve(noise, np.ones(6) / 6, 'same')) * np.exp(-t / 0.6) * 0.35
    return np.tanh(1.4 * boom + crash).astype(np.float32)

def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur
    x = rng.standard_normal(n).astype(np.float32)
    # 区間ごとに平滑化の幅を狭めて「だんだん明るくなる」ノイズ
    out = np.zeros(n, np.float32); blk = 2400
    for s in range(0, n, blk):
        w = int(max(2, 60 * (1 - k[s]) ** 2 + 2))
        out[s:s + blk] = np.convolve(x[max(0, s - w):s + blk], np.ones(w) / w, 'same')[-len(out[s:s + blk]):]
    tone = np.sin(2 * np.pi * np.cumsum(300 + 900 * k ** 2) / SR) * 0.25
    return ((out * 1.5 + tone) * k ** 2.2).astype(np.float32)

def reverb(x, mix=0.25):
    def comb(y, d, gg):
        y = y.copy()
        for s in range(d, len(y), d):
            e = min(s + d, len(y)); y[s:e] += gg * y[s - d:e - d]
        return y
    wet = sum(comb(x, d, gg) for d, gg in ((1601, 0.70), (1867, 0.68), (2129, 0.66), (2423, 0.64))) / 4
    return (1 - mix) * x + mix * wet

def generate(sync):
    S = {s['id']: s for s in sync['scenes']}
    end = lambda sid: S[sid]['start'] + S[sid]['dur']
    total = end('cta')
    n = int(total * SR) + SR
    pad, bass, arp, drums, fx, side = (np.zeros(n, np.float32) for _ in range(6))

    seik_on = sync['seikanHit'] - 0.05
    def section(t):
        if t < S['local']['start']: return 'full'
        if t < S['seikan']['start']: return 'soft'
        if t < seik_on: return 'build'
        if t < S['decline']['start']: return 'full'
        if t < S['compare']['start']: return 'dark'
        if t < S['cta']['start']: return 'break'
        return 'full'

    nb = int(total / BAR) + 2
    K = kick(); C = clap()
    for b in range(nb):
        t0 = b * BAR
        sec = section(t0 + 0.01)
        prog = DARK if sec in ('dark',) else BRIGHT
        chord, root = prog[b % 4]
        # --- パッド(スーパーソウ風) ---
        dur = BAR + 0.4; m = int(dur * SR)
        sig = np.zeros(m, np.float32)
        oct_ = -12 if sec == 'dark' else 0
        for note in chord:
            for det in (-0.006, 0, 0.006):
                sig += saw(midi(note + oct_), m, harm=10, det=det, ph=rng.uniform(0, 6.28)) * 0.33
        pg = {'full': 0.55, 'soft': 0.6, 'build': 0.5, 'dark': 0.6, 'break': 0.55}[sec]
        add(pad, t0, sig * env(m, 0.04 if sec == 'full' else 0.5, 0.4) * pg)
        # --- ベース(8分) ---
        if sec in ('full', 'dark', 'build'):
            for k in range(8):
                if sec == 'build' and k % 2: continue
                m2 = int(BEAT / 2 * SR * 0.92)
                f = midi(root - 12)
                s2 = saw(f, m2, harm=6) * 0.7 + np.sin(2 * np.pi * f * np.arange(m2) / SR)
                add(bass, t0 + k * BEAT / 2, np.tanh(1.5 * s2) * env(m2, 0.005, 0.03) * (1.0 if k % 2 else 0.85))
        # --- 16分アルペジオ ---
        if sec in ('full', 'soft', 'build'):
            pat = [0, 1, 2, 1, 0, 2, 1, 2] * 2
            for k in range(16):
                if sec == 'soft' and k % 2: continue
                note = chord[pat[k] % len(chord)] + 12 + (12 if k in (6, 14) else 0)
                m3 = int(0.22 * SR); tt = np.arange(m3) / SR
                f = midi(note)
                s3 = (np.sign(np.sin(2 * np.pi * f * tt)) * 0.35 + np.sin(2 * np.pi * f * tt)) * np.exp(-tt / 0.07)
                add(arp, t0 + k * BEAT / 4, s3.astype(np.float32) * (0.9 if k % 4 == 0 else 0.6))
        # --- ドラム ---
        for k in range(4):
            tb = t0 + k * BEAT
            if sec == 'full':
                add(drums, tb, K, 1.0); add(side, tb, np.ones(1, np.float32))
                if k in (1, 3): add(drums, tb, C, 0.55)
                add(drums, tb + BEAT / 2, hat(), 0.32); add(drums, tb + BEAT / 4 * 3, hat(dec=0.01), 0.12)
            elif sec == 'dark':
                if k in (0, 2): add(drums, tb, K, 1.0); add(side, tb, np.ones(1, np.float32))
                if k == 2: add(drums, tb, C, 0.5)
                add(drums, tb + BEAT / 2, hat(), 0.18)
            elif sec == 'build':
                add(drums, tb + BEAT / 2, hat(), 0.25)
                if t0 > seik_on - 2 * BAR: add(drums, tb, K, 0.6); add(side, tb, np.ones(1, np.float32))

    # サイドチェイン(キックのたびにパッドとベースを沈める)
    sc_env = np.ones(n, np.float32)
    hits = np.nonzero(side)[0]
    m = int(0.28 * SR); curve = 1 - 0.65 * np.exp(-np.arange(m) / SR / 0.07)
    for h in hits:
        e = min(n, h + m); sc_env[h:e] = np.minimum(sc_env[h:e], curve[:e - h])

    # --- 効果音: シーン頭のスウッシュ、インパクト、ライザー ---
    add(fx, 0.0, impact(), 0.9)
    add(fx, sync['swap'], impact()[: int(1.2 * SR)], 0.55)
    for sid in ('birth', 'trunk', 'north', 'local', 'local2', 'seikan', 'recent', 'cta'):
        add(fx, S[sid]['start'] - 0.5, riser(0.5) * 0.5)
    add(fx, seik_on - 3.0, riser(3.0), 0.9)
    add(fx, seik_on, impact(), 0.9)
    add(fx, S['decline']['start'], impact(), 0.8)
    for e in sync['events']:
        if e['km'] < 0:
            big = abs(e['km']) >= 100
            add(fx, e['t'], tom(70 if big else 120), 0.9 if big else 0.6)
            if big: add(fx, e['t'], impact()[: int(1.0 * SR)], 0.45)
    add(fx, S['compare']['start'] - 1.2, riser(1.2), 0.6)
    add(fx, sync['compareHit'], impact(), 1.0)
    add(fx, S['cta']['start'], impact(), 0.7)

    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    music = 0.42 * reverb(norm(pad), 0.3) * sc_env + 0.32 * norm(bass) * sc_env + 0.22 * reverb(norm(arp), 0.35) + 0.6 * norm(drums)
    mix = music + 0.55 * reverb(norm(fx), 0.25)
    mix = np.tanh(1.3 * mix) / np.tanh(1.3)
    mix = mix[: int(total * SR)]
    mix *= env(len(mix), 0.02, 2.2)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    sync = json.load(open(os.path.join(HERE, 'output', 'sync.json')))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'bgm.wav')
    x = generate(sync)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
