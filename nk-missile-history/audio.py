# -*- coding: utf-8 -*-
"""軍事ドキュメンタリー風 BGM と効果音を numpy/scipy だけで合成し、ナレーションとミックスして動画に載せる。
外部音源は使わないため権利フリー。Jアラートの実際の警報音には似せない(誤認防止)。
入力: output/timeline.json, output/narration.wav, output/video_silent.mp4
出力: output/bgm.wav, output/sfx.wav, output/mix.wav, output/video_narrated.mp4
"""
import os, json, wave, subprocess
import numpy as np
from scipy.signal import butter, sosfilt, sawtooth

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
rng = np.random.default_rng(20261104)
tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
TOTAL = tl['total']; N = int(TOTAL * SR)
SC = {s['id']: s for s in tl['scenes']}

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tt(n): return np.arange(n) / SR
def add(buf, t0, x, g=1.0):
    s = int(round(t0 * SR));
    if s < 0: x = x[-s:]; s = 0
    e = min(s + len(x), len(buf))
    if e > s: buf[s:e] += g * x[:e - s]
def lp(x, fc, order=2): return sosfilt(butter(order, min(fc, SR / 2 - 100) / (SR / 2), 'low', output='sos'), x)
def hp(x, fc, order=2): return sosfilt(butter(order, fc / (SR / 2), 'high', output='sos'), x)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos'), x)
def env(n, a, d):  # アタック a 秒・指数減衰 d 秒
    t = tt(n); e = np.exp(-t / d); na = max(1, int(a * SR)); e[:na] *= np.linspace(0, 1, na); return e
def noise(n): return rng.standard_normal(n)
def norm(x, p=1.0): return x / (np.max(np.abs(x)) + 1e-9) * p
def sweep_lp(x, f0, f1, curve=2.0):
    """カットオフが f0→f1 に動く 1 次ローパス(時間変化)"""
    n = len(x); fc = f0 + (f1 - f0) * np.linspace(0, 1, n) ** curve
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty(n); s = 0.0
    for i in range(n): s = (1 - a[i]) * x[i] + a[i] * s; y[i] = s
    return y
def section(t):
    for s in tl['scenes'][::-1]:
        if t >= s['start']: return s['id']
    return 'hook'

# ================= 楽器 =================
def ostinato_note(f, dur=0.14, bright=1.0):
    n = int(dur * SR); t = tt(n)
    x = sawtooth(2 * np.pi * f * t) + 0.6 * sawtooth(2 * np.pi * f * 1.004 * t) + 0.5 * np.sin(2 * np.pi * f / 2 * t)
    return lp(x, 650 + 900 * bright) * env(n, 0.004, 0.07)
def taiko(f0=90, dur=0.9):
    n = int(dur * SR); t = tt(n); f = 42 + (f0 - 42) * np.exp(-t / 0.06)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.28)
    return body + 0.3 * lp(noise(n), 900) * np.exp(-t / 0.02)
def snare(acc=1.0):
    n = int(0.22 * SR); t = tt(n)
    x = 0.8 * bp(noise(n), 1500, 7000) * np.exp(-t / 0.075) + 0.6 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04)
    return x * acc
def braam(notes=(38, 45, 50, 53), dur=3.2):
    """重いブラスのヒット(低音 D マイナー)"""
    n = int(dur * SR); t = tt(n); x = np.zeros(n)
    for m in notes:
        for det in (-0.006, 0, 0.007):
            x += sawtooth(2 * np.pi * midi(m) * (1 + det) * t + rng.uniform(0, 6))
    x = sweep_lp(x, 2400, 180, 0.6) * env(n, 0.02, 1.4)
    x += 1.2 * np.sin(2 * np.pi * midi(26) * t) * env(n, 0.01, 1.2)      # サブベース
    return x
def boom(dur=1.6, f0=70, f1=28):
    n = int(dur * SR); t = tt(n); f = f1 + (f0 - f1) * np.exp(-t / 0.12)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.5) + 0.5 * lp(noise(n), 300) * np.exp(-t / 0.18)
def crash(dur=2.2):
    n = int(dur * SR); return hp(noise(n), 4000) * env(n, 0.002, 0.7)
def riser(dur=1.8):
    n = int(dur * SR); t = tt(n); x = bp(noise(n), 400, 9000) * (t / dur) ** 2.2
    f = 120 + 900 * (t / dur) ** 2; x += 0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) ** 2
    return x
def pad(notes, dur):
    n = int(dur * SR); t = tt(n); x = np.zeros(n)
    for m in notes:
        for h in range(1, 6):
            x += (1 / h ** 1.6) * np.sin(2 * np.pi * midi(m) * h * t * (1 + 0.0015 * np.sin(2 * np.pi * 0.3 * t)) + rng.uniform(0, 6))
    a = min(1.0, dur / 3); e = np.ones(n); na = int(a * SR); e[:na] = np.linspace(0, 1, na); e[-na:] = np.linspace(1, 0, na)
    return x * e
def reverb(x, mix=0.25):
    def comb(x, d, g):
        y = x.copy()
        for s in range(d, len(y), d): e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
        return y
    wet = sum(comb(x, d, g) for d, g in ((1553, .72), (1877, .7), (2251, .68), (3001, .6))) / 4
    return (1 - mix) * x + mix * lp(wet, 5000)

# ================= BGM =================
BPM = 100; B = 60 / BPM; S16 = B / 4; BAR = 4 * B
ROOTS = [38, 34, 36, 33]               # D, Bb, C, A (低音)
CHORDS = [[50, 53, 57], [46, 50, 53], [48, 52, 55], [45, 49, 52]]
# セクションごとの強度: ostinato, taiko, snare, brass, pad
INT = {'hook': (0, .5, 0, 0, .7), 'y1990': (.55, .6, 0, 0, .8), 'y2000': (.7, .7, .25, 0, .8), 'y2016': (1, 1, .9, .6, .7),
       'chart': (.9, .8, .6, .4, .6), 'y2022': (1, 1, 1, .7, .7), 'quality': (.35, .3, 0, 0, 1), 'now': (.8, .8, .7, .3, .8), 'outro': (0, 0, 0, 0, .9)}
def bgm():
    ost = np.zeros(N); drm = np.zeros(N); sn = np.zeros(N); br = np.zeros(N); pd = np.zeros(N); fx = np.zeros(N)
    nb = int(np.ceil(TOTAL / BAR))
    for b in range(nb):
        t0 = b * BAR; ci = (b // 1) % 4; root = ROOTS[ci]
        sec = section(t0 + 0.01)
        io, it, isn, ib, ip = INT[sec]
        pd_dur = BAR + 1.0
        add(pd, t0, pad(CHORDS[ci], pd_dur) + 0.8 * pad([root + 12], pd_dur), ip)
        for k in range(16):
            t = t0 + k * S16
            s2 = section(t + 0.01); io2, it2, isn2, ib2, _ = INT[s2]
            # ギャロップ型の刻み(タタタン)
            if io2 and k % 4 != 1:
                f = midi(root + (12 if k in (6, 14) else 0)); add(ost, t, ostinato_note(f, bright=io2), io2 * (1.0 if k % 4 == 0 else 0.7))
            if it2 and k in (0, 8): add(drm, t, taiko(), it2)
            if it2 and k in (6, 14) and it2 > .6: add(drm, t, taiko(75, .5), .55 * it2)
            if isn2:  # マーチングスネア
                pat = [1, 0, .35, .5, .8, 0, .35, .45, 1, 0, .35, .5, .8, .4, .6, .8]
                if pat[k]: add(sn, t, snare(pat[k]), isn2)
        if ib and b % 2 == 0: add(br, t0, braam(notes=(root, root + 7, root + 12), dur=1.4), ib * 0.55)
    # 大きな節目: BRAAM + ブーム + クラッシュ、直前にライザーやスネアロール
    def big(t, g=1.0, rise=0.0, roll=0.0):
        add(fx, t, braam(), g); add(fx, t, boom(), 0.9 * g); add(fx, t, crash(), 0.35 * g)
        if rise: r = riser(rise); add(fx, t - rise, r, 0.5 * g)
        if roll:
            n32 = int(roll / (S16 / 2))
            for i in range(n32): add(fx, t - roll + i * S16 / 2, snare(0.25 + 0.75 * i / n32), 0.6 * g)
    title = next(c['t'] for c in SC['hook']['cues'] if c.get('id') == 'title')
    big(title, 1.0, rise=1.4, roll=1.2)
    big(SC['y2016']['start'], 0.8, roll=1.0)
    peak = next(c['t'] for c in SC['chart']['cues'] if c['type'] == 'peak')
    big(peak + 0.55, 1.1, rise=1.6, roll=1.5)
    big(SC['y2022']['start'], 0.7)
    big(SC['now']['start'], 0.6, rise=1.2)
    big(SC['outro']['start'], 1.0, roll=1.2)
    # quality: 時計のような刻み(緊張感)
    q = SC['quality']
    for i in range(int(q['dur'] / B * 2)):
        t = q['start'] + i * B / 2; n = int(0.03 * SR)
        add(fx, t, hp(noise(n), 3000) * env(n, 0.001, 0.008), 0.25 if i % 2 else 0.4)
    # 冒頭のドローン
    n = int(6.0 * SR); tq = tt(n)
    add(fx, 0, (np.sin(2 * np.pi * midi(26) * tq) + 0.4 * sawtooth(2 * np.pi * midi(38) * tq)) * np.minimum(1, tq / 0.3) * np.exp(-tq / 4), 0.35)
    mix = 0.42 * norm(ost) + 0.55 * norm(drm) + 0.30 * norm(sn) + 0.30 * norm(br) + 0.28 * norm(pd) + 0.75 * norm(fx)
    mix = reverb(mix, 0.2)
    # 最後 3 秒フェードアウト
    f = int(3.0 * SR); mix[-f:] *= np.linspace(1, 0, f) ** 1.5
    return norm(mix, 0.9)

# ================= 効果音 =================
def whoosh(dur, big=True):
    n = int(dur * SR); t = tt(n)
    x = sweep_lp(noise(n), 300, 3500 if big else 2200, 1.0) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
    rumble = lp(noise(n), 120) * np.exp(-t / (dur * 0.6))
    return x + (1.5 * rumble if big else 0.4 * rumble)
def thud():
    n = int(0.5 * SR); t = tt(n); f = 40 + 120 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.15) + 0.4 * bp(noise(n), 800, 4000) * np.exp(-t / 0.03)
def tick(f=2400): n = int(0.025 * SR); t = tt(n); return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006)
def ping(f=1300): n = int(0.8 * SR); t = tt(n); return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.18)
def warn_tone():
    """警告音: 低い 2 連パルス(サイレンや J アラートの音には似せない)"""
    n = int(0.32 * SR); t = tt(n); x = sawtooth(2 * np.pi * 147 * t, 0.5) + 0.5 * sawtooth(2 * np.pi * 147.8 * t, 0.5)
    return lp(x, 1200) * env(n, 0.01, 0.12)
def glitch():
    n = int(0.14 * SR); t = tt(n); x = np.sign(np.sin(2 * np.pi * 90 * t)) * bp(noise(n), 300, 5000)
    return x * np.exp(-t / 0.05)
def sfx():
    x = np.zeros(N)
    for i, s in enumerate(tl['scenes']):
        if i: add(x, s['start'], glitch(), 0.35); r = whoosh(0.45, False)[::-1]; add(x, s['start'] - 0.45, r, 0.35)
        for c in s['cues']:
            ty, t = c['type'], c['t']
            if ty == 'missile':
                add(x, t, whoosh(c['dur'] + 0.4, c.get('big', False)), 0.45 if c.get('big') else 0.3)
                add(x, t, boom(0.8, 90, 40), 0.35)
                if c.get('impact'): add(x, t + c['dur'], boom(1.4, 80 if c.get('eez') else 60, 25), 1.0 if c.get('eez') else 0.6)
            elif ty == 'salvo':
                for k in range(c['n']):
                    add(x, t + k * c['step'], whoosh(c['dur'] + 0.2, False), 0.2)
                    add(x, t + k * c['step'] + c['dur'], boom(0.7, 70, 35), 0.25)
            elif ty == 'stamp' and c.get('id') != 'title': add(x, t + 0.12, thud(), 0.8)
            elif ty == 'year':
                for k in range(6): add(x, t + k * 0.06, tick(1800 + 150 * k), 0.25)
            elif ty == 'count':
                d = c['dur']; k = 0; tk = 0.0
                while tk < d: add(x, t + tk, tick(2200), 0.18); k += 1; tk = d * (k / 26) ** 1.6
                add(x, t + d, thud(), 0.5)
            elif ty == 'bars':
                for k in range(6): add(x, t + k * 0.22, whoosh(0.35, False), 0.25); add(x, t + k * 0.22 + 0.3, tick(900), 0.3)
            elif ty == 'zero':
                n = int(0.6 * SR); tq = tt(n); f = 220 * np.exp(-tq / 0.3) + 60
                add(x, t, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tq / 0.25), 0.4)
            elif ty == 'peak': add(x, t + 1.3, thud(), 0.7)
            elif ty == 'warn':
                for k in range(4): add(x, t + k * 0.5, warn_tone(), 0.5); add(x, t + k * 0.5 + 0.16, warn_tone(), 0.4)
            elif ty == 'card': add(x, t, whoosh(0.4, False), 0.4); add(x, t + 0.25, thud(), 0.55)
            elif ty == 'dots':
                for k in range(c['n']): add(x, t + 0.25 + k * c['step'], ping(1100 + 60 * k), 0.3)
            elif ty == 'eez':
                for k in range(3): add(x, t + k * 0.3, ping(700), 0.2)
    # 「今日も発射」スタンプ
    dc = next(c for c in SC['now']['cues'] if c['type'] == 'dots')
    add(x, dc['t'] + 0.25 + (dc['n'] - 1) * dc['step'] + 0.42, thud(), 0.8)
    return norm(reverb(x, 0.12), 0.9)

def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    music = bgm(); write(os.path.join(OUT, 'bgm.wav'), music); print('bgm ok')
    fx = sfx(); write(os.path.join(OUT, 'sfx.wav'), fx); print('sfx ok')
    with wave.open(os.path.join(OUT, 'narration.wav')) as w:
        voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
    # ダッキング: ナレーション中は BGM を下げる(アタック速く・リリース 0.4 秒)
    hop = SR // 50
    rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
    e = np.zeros_like(rms)
    for i, v in enumerate(rms): e[i] = max(v, (e[i - 1] if i else 0) * 0.95)
    e = np.pad(np.repeat(e, hop), (0, N - len(rms) * hop))
    sp = np.clip(e / 0.08, 0, 1)
    k = SR // 20; sp = np.convolve(sp, np.ones(k) / k, mode='same')
    g_music = 0.55 - 0.33 * sp          # 無音時 0.55 / 発話時 0.22
    g_fx = 0.30 - 0.12 * sp          # 効果音: 無音時 0.30 / 発話時 0.18
    mix = 1.0 * voice + music * g_music + fx * g_fx
    # 軽いソフトクリップで音圧を整える
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    write(os.path.join(OUT, 'mix.wav'), norm(mix, 0.95)); print('mix ok')
    src = os.path.join(OUT, 'video_silent.mp4'); dst = os.path.join(OUT, 'video_narrated.mp4')
    if os.path.exists(src):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', os.path.join(OUT, 'mix.wav'),
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
        print('wrote', dst)
