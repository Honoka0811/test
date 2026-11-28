# -*- coding: utf-8 -*-
"""BGM と効果音を numpy だけで合成し(外部音源なし・権利フリー)、掛け合い音声とミックスする。
入力: build/timeline.json, build/voice.wav(script.py が生成)
出力: build/bgm.wav(BGM のみ), build/mix.wav(完成ミックス 48kHz stereo)

BGM: F メジャー / 136BPM の跳ねる 2 ビート。ベース・裏打ちのコード・トイピアノ風メロディ・
     キック/クラップ/ハイハット・そり鈴(冬っぽさ)。1位発表の直前で止まり、1位でファンファーレとともに再開。
"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
SR = 48000
TL = json.load(open(os.path.join(BUILD, 'timeline.json'), encoding='utf-8'))
TOTAL = TL['total']
N = int(TOTAL * SR)
rng = np.random.default_rng(11)

BPM = 136
BEAT = 60 / BPM
STEP = BEAT / 2          # 8分音符
BAR = BEAT * 4

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tt(n): return np.arange(n) / SR

def add(buf, t0, sig, gain=1.0, pan=0.0):
    """buf: (N,2)。pan -1(左)〜+1(右)"""
    s = int(round(t0 * SR))
    if s >= len(buf) or len(sig) == 0: return
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf))
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    if sig.ndim == 1:
        buf[s:e, 0] += sig[:e - s] * gain * l * 1.414
        buf[s:e, 1] += sig[:e - s] * gain * r * 1.414
    else:
        buf[s:e] += sig[:e - s] * gain

def env(n, a=0.003, d=0.2, sustain=False):
    t = tt(n)
    e = np.exp(-t / d) if not sustain else np.ones(n)
    na = max(1, int(a * SR)); e[:na] *= np.linspace(0, 1, na)
    return e

def band_noise(n, lo, hi):
    x = rng.standard_normal(n)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.max(np.abs(y)) + 1e-9)

def fade(sig, fi=0.002, fo=0.01):
    n = len(sig); a, b = min(n, int(fi * SR)), min(n, int(fo * SR))
    if a: sig[:a] *= np.linspace(0, 1, a)
    if b: sig[-b:] *= np.linspace(1, 0, b)
    return sig

# ---------------- 楽器 ----------------
def saw(f, n, maxh=None, cutoff=1400):
    t = tt(n); y = np.zeros(n)
    H = int(min(cutoff, SR / 2 - 100) // f) if maxh is None else maxh
    for h in range(1, max(1, H) + 1):
        y += np.sin(2 * np.pi * f * h * t) / h
    return y * 0.55

def bass_note(m, dur):
    n = int(dur * SR); f = midi(m)
    y = saw(f, n, cutoff=900) * env(n, .004, .16) + 0.6 * np.sin(2 * np.pi * f * tt(n)) * env(n, .004, .22)
    return fade(y, .002, .02)

def stab(notes, dur=0.16):
    n = int(dur * SR); y = np.zeros(n); t = tt(n)
    for m in notes:
        f = midi(m)
        for h, a in ((1, 1), (2, .5), (3, .32), (4, .18), (6, .08)):
            y += a * np.sin(2 * np.pi * f * h * t + h)
    return fade(y * env(n, .004, .07) / len(notes), .003, .03)

def toy(m, dur=0.5):
    n = int(dur * SR); f = midi(m); t = tt(n)
    y = (np.sin(2 * np.pi * f * t) + .45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / .12)
         + .18 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / .06) + .25 * np.sin(2 * np.pi * 4.2 * f * t) * np.exp(-t / .02))
    return fade(y * env(n, .002, .28), .001, .05)

def kick():
    n = int(.32 * SR); t = tt(n)
    f = 45 + 110 * np.exp(-t / .035)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .14)
    y[:240] += band_noise(240, 1000, 6000) * .3
    return y

NOISE_MID = band_noise(SR * 2, 900, 5000)
NOISE_HI = band_noise(SR * 2, 6000, 16000)
NOISE_WIDE = band_noise(SR * 4, 200, 12000)
def chunk(src, n):
    s = rng.integers(0, len(src) - n); return src[s:s + n].copy()

def clap():
    n = int(.2 * SR); y = np.zeros(n)
    for k, d in enumerate((0, .009, .018)):
        s = int(d * SR); m = n - s
        y[s:] += chunk(NOISE_MID, m) * np.exp(-tt(m) / (.008 if k < 2 else .07))
    return y * .8

def hat(open_=False):
    n = int((.16 if open_ else .05) * SR)
    return chunk(NOISE_HI, n) * np.exp(-tt(n) / (.05 if open_ else .012))

def sleigh():
    n = int(.09 * SR); t = tt(n)
    tone = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (4970, 6310, 7880, 9120))
    return (chunk(NOISE_HI, n) * .5 + tone * .25) * np.exp(-t / .025) * (1 + .6 * np.sin(2 * np.pi * 38 * t))

# ---------------- BGM ----------------
PROG = [  # (ベースのルート, 裏打ちコード)
    (41, [65, 69, 72]),  # F
    (36, [64, 67, 72]),  # C
    (38, [62, 65, 69]),  # Dm
    (34, [62, 65, 70]),  # Bb
    (41, [65, 69, 72]),  # F
    (36, [64, 67, 72]),  # C
    (34, [62, 65, 70]),  # Bb
    (36, [64, 67, 72]),  # C
]
_ = '-'
MELODY = [
    [81, _, 84, _, 81, 79, 77, _],
    [79, _, 76, _, 79, _, None, None],
    [77, _, 81, _, 86, _, 84, 81],
    [82, _, _, _, None, None, 81, 82],
    [84, _, 89, _, 86, 84, 81, _],
    [86, _, 84, _, 79, _, 76, _],
    [77, 79, 82, _, 81, _, 79, _],
    [79, 81, 79, 76, 72, _, None, None],
]
BASS_PAT = [0, None, 12, 0, 7, None, 12, 7]  # 8分ごとの音程(ルートからの半音)

def bgm_segment(length, extra=False):
    """長さ length 秒の BGM(stereo)。extra=True で 1位以降の盛り上げ(タンバリン追加・音量少し上げ)"""
    n = int(length * SR) + SR
    buf = np.zeros((n, 2))
    nbars = int(np.ceil(length / BAR)) + 1
    for b in range(nbars):
        root, chord = PROG[b % 8]
        t0 = b * BAR
        for k in range(8):
            ts = t0 + k * STEP
            if ts > length: break
            # ドラム
            if k in (0, 4) or (k == 7 and b % 2 == 1): add(buf, ts, kick(), .95)
            if k in (2, 6): add(buf, ts, clap(), .42, .05)
            add(buf, ts, hat(open_=(k == 7)), .16 if k % 2 else .1, .3)
            for q in range(2):  # そり鈴は 16 分
                add(buf, ts + q * STEP / 2, sleigh(), (.10 if (k % 2 == 0 and q == 0) else .055) * (1.35 if extra else 1), .55)
            if extra and k % 2 == 1: add(buf, ts, hat(True), .08, -.5)
            # ベース
            iv = BASS_PAT[k]
            if iv is not None: add(buf, ts, bass_note(root + iv, STEP * .95), .34)
            # 裏打ちのコード
            if k % 2 == 1: add(buf, ts, stab(chord), .30, -.25)
            # メロディ
            m = MELODY[b % 8][k]
            if isinstance(m, int):
                hold = 1
                while k + hold < 8 and MELODY[b % 8][k + hold] == _: hold += 1
                sig = toy(m, max(.35, STEP * hold + .25))
                add(buf, ts, sig, .26, .12)
                add(buf, ts + STEP * 1.5, sig * .35, .26, -.4)  # 付点8分のディレイ
    return buf[:int(length * SR)] * (1.12 if extra else 1.0)

# ---------------- 効果音 ----------------
def sfx_whoosh(dur=.5):
    n = int(dur * SR); t = tt(n); x = chunk(NOISE_WIDE, n)
    # 帯域を時間で動かす: 短い窓ごとに FFT マスク
    out = np.zeros(n); win = 1024; hop = 512; w = np.hanning(win)
    for s in range(0, n - win, hop):
        p = s / n; c = 600 + 5200 * np.sin(p * np.pi)
        X = np.fft.rfft(x[s:s + win] * w); f = np.fft.rfftfreq(win, 1 / SR)
        X *= np.exp(-((np.log(f + 1) - np.log(c)) ** 2) / .35)
        out[s:s + win] += np.fft.irfft(X, win)
    out *= np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    out /= np.max(np.abs(out)) + 1e-9
    pan = np.linspace(.8, -.8, n)  # 帯は右→左
    return np.stack([out * np.cos((pan + 1) * np.pi / 4), out * np.sin((pan + 1) * np.pi / 4)], 1) * 1.3

def sfx_stamp():
    n = int(.6 * SR); t = tt(n)
    f = 38 + 140 * np.exp(-t / .05)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .22)
    m = int(.07 * SR); y[:m] += chunk(NOISE_MID, m) * np.exp(-tt(m) / .015) * .8
    y += .35 * np.sign(np.sin(2 * np.pi * 190 * t)) * np.exp(-t / .03)
    return y

def sfx_plop():
    n = int(.45 * SR); t = tt(n)
    f = 60 + 90 * np.exp(-t / .06)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .12)
    m = int(.3 * SR); y[int(.02 * SR):int(.02 * SR) + m] += band_noise(m, 1500, 7000) * np.exp(-tt(m) / .07) * .35
    return y

def sfx_pop():
    n = int(.12 * SR); t = tt(n)
    f = 380 + 1300 * (t / t[-1]) ** .6
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .04)

def sfx_tick():
    n = int(.09 * SR); t = tt(n)
    return (np.sin(2 * np.pi * 1750 * t) + .5 * np.sin(2 * np.pi * 2630 * t)) * np.exp(-t / .018)

def sfx_boing():
    n = int(.5 * SR); t = tt(n)
    f = 230 + 420 * np.exp(-t / .09) + 55 * np.sin(2 * np.pi * 16 * t) * np.exp(-t / .25)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) + .25 * np.sin(4 * np.pi * np.cumsum(f) / SR)) * env(n, .003, .16)

def sfx_sparkle():
    out = np.zeros((int(.9 * SR), 2))
    for i, m in enumerate((96, 100, 103, 108, 112)):
        add(out, i * .055, toy(m, .45) * .5, 1, -.6 + i * .3)
    return out

def sfx_rattle(dur):
    out = np.zeros(int(dur * SR) + SR); tcur = 0.0; i = 0
    while tcur < dur:
        n = int(.025 * SR); t = tt(n)
        click = (chunk(NOISE_HI, n) * .5 + np.sin(2 * np.pi * (2400 + 300 * (i % 3)) * t)) * np.exp(-t / .006)
        g = .7 + .3 * rng.random(); g *= 1 if tcur < dur * .7 else (1 - (tcur - dur * .7) / (dur * .3))
        s = int(tcur * SR); out[s:s + n] += click * g
        tcur += 1 / 15 + rng.uniform(-.012, .012); i += 1
    return out[:int(dur * SR)]

def sfx_drumroll(dur):
    n = int(dur * SR); out = np.zeros(n + SR); tcur = 0.0
    while tcur < dur:
        p = tcur / dur
        rate = 18 + 14 * p
        m = int(.06 * SR); t = tt(m)
        hit = chunk(NOISE_MID, m) * np.exp(-t / .02) + .5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / .015)
        s = int(tcur * SR); out[s:s + m] += hit * (.18 + .82 * p ** 1.6) * (.85 + .3 * rng.random())
        tcur += 1 / rate
    out = out[:n]
    # 上昇音(ライザー)
    t = tt(n); f = 180 * 2 ** (2.2 * t / dur)
    riser = sum(np.sin(2 * np.pi * np.cumsum(f * h) / SR) / h for h in (1, 2, 3)) * (t / dur) ** 2 * .22
    return out + riser

def sfx_crash():
    n = int(2.4 * SR); t = tt(n)
    y = band_noise(n, 3000, 16000) * np.exp(-t / .5) * .8
    kk = kick(); y[:len(kk)] += kk * 1.2
    return y

def sfx_fanfare():
    out = np.zeros((int(2.2 * SR), 2))
    def brass(notes, dur, gain):
        n = int(dur * SR); t = tt(n); y = np.zeros(n)
        vib = 1 + .004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / .3, 0, 1)
        for m in notes:
            f = midi(m) * vib
            ph = 2 * np.pi * np.cumsum(f) / SR
            for h in range(1, 9): y += np.sin(ph * h) / h ** 1.1
        a = np.clip(t / .03, 0, 1); r = np.clip((dur - t) / .12, 0, 1)
        return y * a * r * gain / len(notes)
    add(out, 0.00, brass([72, 76], .14, .9), 1, -.1)
    add(out, 0.16, brass([72, 76], .14, .9), 1, .1)
    add(out, 0.32, brass([65, 69, 72, 77], .52, 1.1), 1, 0)
    add(out, 0.32, bass_note(41, .5) * .9, 1, 0)
    return out

def sfx_lidpop():
    n = int(.25 * SR); t = tt(n)
    f = 220 + 900 * (t / t[-1]) ** .5
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .08) + band_noise(n, 2000, 9000) * np.exp(-t / .03) * .4

DUCKED_FX = {'fanfare', 'drumroll', 'rattle', 'crash'}
SFX = {  # 種類: (生成関数, ゲイン, パン)
    'whoosh': (lambda e: sfx_whoosh(), .30, 0), 'stamp': (lambda e: sfx_stamp(), .30, 0), 'plop': (lambda e: sfx_plop(), .28, 0),
    'pop': (lambda e: sfx_pop(), .18, .1), 'tick': (lambda e: sfx_tick(), .17, -.1), 'boing': (lambda e: sfx_boing(), .13, .2),
    'sparkle': (lambda e: sfx_sparkle(), .24, 0), 'rattle': (lambda e: sfx_rattle(e['dur']), .20, .15),
    'drumroll': (lambda e: sfx_drumroll(e['dur']), .50, 0), 'crash': (lambda e: sfx_crash(), .40, 0),
    'fanfare': (lambda e: sfx_fanfare(), .34, 0), 'lidpop': (lambda e: sfx_lidpop(), .34, 0),
}

def read_wav(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    return x

def write_wav(p, x):
    x = np.clip(x, -1, 1)
    with wave.open(p, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())

def main():
    sc = {s['id']: s for s in TL['scenes']}
    drum, r1 = sc['drum'], sc['r1']
    # --- BGM ---
    bgm = np.zeros((N, 2))
    a_len = drum['start'] + .35
    seg = bgm_segment(a_len)
    fo = int(.35 * SR); seg[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    bgm[:len(seg)] += seg
    b0 = r1['start'] + r1['ev']['l1end'] + .05   # 「キムチ鍋〜！！」を言い終えたら BGM 再開
    b_len = TOTAL - b0
    seg = bgm_segment(b_len, extra=True)
    fo = int(1.4 * SR); seg[-fo:] *= np.linspace(1, 0, fo)[:, None]
    add(bgm, b0, seg)
    # --- 効果音 ---
    fx = np.zeros((N, 2)); fxd = np.zeros((N, 2))   # fxd: 声の間は下げる長い効果音
    for e in TL['sfx']:
        fn, g, pan = SFX[e['type']]
        add(fxd if e['type'] in DUCKED_FX else fx, e['t'], fn(e), g, pan)
    # --- 声 + ダッキング ---
    voice = read_wav(os.path.join(BUILD, 'voice.wav'))
    voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
    hop = SR // 50
    rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
    envl = np.zeros_like(rms)
    for i, v in enumerate(rms): envl[i] = max(v, (envl[i - 1] if i else 0) * .93)  # リリース約 0.3 秒
    envl = np.pad(np.repeat(envl, hop), (0, N - len(envl) * hop))
    k = SR // 20; envl = np.convolve(envl, np.ones(k) / k, mode='same')
    speech = np.clip(envl / .05, 0, 1)
    duck = 1 - .78 * speech              # 発話中は BGM を約 -13dB
    write_wav(os.path.join(BUILD, 'bgm.wav'), bgm / (np.max(np.abs(bgm)) + 1e-9) * .9)
    vpart, mpart = voice[:, None] * 1.0, bgm * (duck * .24)[:, None]
    fpart = fx * (.9 * (1 - .4 * speech))[:, None] + fxd * (.9 * (1 - .65 * speech))[:, None]
    mix = vpart + mpart + fpart
    sp = speech > .5
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    print(f'発話中  声 {db(vpart[sp]):.1f} dB / BGM {db(mpart[sp]):.1f} dB / 効果音 {db(fpart[sp]):.1f} dB')
    print(f'無音時  BGM {db(mpart[~sp]):.1f} dB / 効果音 {db(fpart[~sp]):.1f} dB')
    # ソフトリミッタ
    peak = np.max(np.abs(mix)); mix = mix / peak * 1.25
    mix = np.tanh(mix) / np.tanh(1.25) * .97
    write_wav(os.path.join(BUILD, 'mix.wav'), mix)
    print('wrote build/bgm.wav, build/mix.wav', f'{TOTAL:.2f}s')

if __name__ == '__main__':
    main()
