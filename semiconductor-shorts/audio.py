# -*- coding: utf-8 -*-
"""BGM と効果音をプログラムで合成し(外部音源なし・権利フリー)、ナレーションとミックスして動画に合成する。

BGM: Aマイナーのエレクトロ(Am-F-C-G)。台湾(TSMC)の場面の頭でサビ(ドロップ)が鳴るようにテンポを逆算する。
  イントロ(冒頭から四つ打ち) → ビルド → スネアロール+ライザー → ドロップ → 日本パート(明るめ) → ブレイク(CTA)
効果音: render.html が書き出した output/events.json の時刻・種類どおりに配置する。
ナレーション中は BGM を自動で下げる(ダッキング)。

使い方: python3 audio.py   (narrate.py と capture.js の後に実行)
出力: output/bgm.wav, output/sfx.wav, output/mix.wav, output/semiconductor_short.mp4
"""
import os, json, wave, subprocess
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
TL = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
TOTAL = TL['total']
N = int(TOTAL * SR) + 1
SCN = {s['id']: s for s in TL['scenes']}
rng = np.random.default_rng(42)

# ---------------- 共通 ----------------
def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def tt(d): return np.arange(int(d * SR)) / SR
def add(buf, t0, sig, g=1.0):
    s = int(round(t0 * SR))
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), buf.shape[-1])
    if e > s: buf[..., s:e] += g * sig[..., :e - s]
def env(n, a, r, total=None):
    e = np.ones(n, np.float32); na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[n - nr:] *= np.linspace(1, 0, nr)
    return e
def noise(d): return rng.standard_normal(int(d * SR)).astype(np.float32)
def saw(f, d, phase=0.0):
    t = tt(d); return (2 * ((f * t + phase) % 1.0) - 1).astype(np.float32)
def sweep(f0, f1, d, curve='exp'):
    t = tt(d); k = t / d
    f = f0 * (f1 / f0) ** k if curve == 'exp' else f0 + (f1 - f0) * k
    return np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)
def norm(x, peak=1.0): return x / (np.max(np.abs(x)) + 1e-9) * peak
def reverb(x, mix=.25, size=1.0):
    y = np.zeros_like(x)
    for d, g in ((1553, .70), (1877, .68), (2251, .66), (2719, .64)):
        d = int(d * size); c = x.copy()
        for s in range(d, len(c), d):
            e = min(s + d, len(c)); c[s:e] += g * c[s - d:e - d]
        y += c
    y = lp(y / 4, 6000)
    return (1 - mix) * x + mix * y

# ---------------- テンポ・構成 ----------------
DROP_T = SCN['tsmc']['s']
BARS_TO_DROP = max(8, round(DROP_T / (240 / 128)))
BPM = 240 * BARS_TO_DROP / DROP_T
BEAT = 60 / BPM; BAR = 4 * BEAT
def bar_of(t): return int(round(t / BAR))
B_BUILD = bar_of(SCN['purity']['s'])
B_DROP = BARS_TO_DROP
B_JAPAN = bar_of(SCN['japan']['s'])
B_CTA = bar_of(SCN['cta']['s'])
NBARS = int(np.ceil(TOTAL / BAR)) + 1
print(f'BPM {BPM:.2f}  bar {BAR:.3f}s  build@{B_BUILD} drop@{B_DROP} japan@{B_JAPAN} cta@{B_CTA} bars={NBARS}')

PROG = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
PROG_JP = [[53, 57, 60], [55, 59, 62], [52, 55, 59], [57, 60, 64]]  # F G Em Am(明るめ)
ROOT = [45, 41, 48, 43]; ROOT_JP = [41, 43, 40, 45]
def section(b):
    if b < B_BUILD: return 'intro'
    if b < B_DROP - 2: return 'build'
    if b < B_DROP: return 'pre'
    if b < B_JAPAN: return 'drop'
    if b < B_CTA: return 'japan'
    return 'break'

def kick():
    d = .42; t = tt(d)
    body = sweep(160, 42, d) * np.exp(-t / .16)
    click = hp(noise(d), 2000) * np.exp(-t / .006) * .3
    return (body + click).astype(np.float32)
def clap():
    d = .3; t = tt(d); x = np.zeros(len(t), np.float32)
    for o in (0, .011, .022):
        s = int(o * SR); m = len(x) - s; n = noise(1.0)[:m] * np.exp(-np.arange(m) / SR / (.012 if o < .02 else .09)); x[s:] += n
    return bp(x, 900, 5000) * 1.4
def hat(open_=False):
    d = .25 if open_ else .05; t = tt(d)
    return hp(noise(d), 7000, 4) * np.exp(-t / (.07 if open_ else .012))
def snare():
    d = .2; t = tt(d)
    return (bp(noise(d), 1500, 7000) * np.exp(-t / .05) + np.sin(2 * np.pi * 190 * t) * np.exp(-t / .04) * .6).astype(np.float32)

def bgm():
    L = np.zeros(N, np.float32); R = np.zeros(N, np.float32)
    drums = np.zeros(N, np.float32); bass = np.zeros(N, np.float32)
    pad = np.zeros((2, N), np.float32); lead = np.zeros((2, N), np.float32); fx = np.zeros(N, np.float32)
    K, CL, HC, HO, SN = kick(), clap(), hat(), hat(True), snare()
    kicks = []
    for b in range(NBARS):
        t0 = b * BAR; sec = section(b)
        if t0 > TOTAL: break
        jp = sec == 'japan'
        chord = (PROG_JP if jp else PROG)[b % 4]; root = (ROOT_JP if jp else ROOT)[b % 4]
        # ---- ドラム ----
        if sec in ('intro', 'build', 'drop', 'japan'):
            for k in range(4):
                add(drums, t0 + k * BEAT, K, 1.0); kicks.append(t0 + k * BEAT)
        if sec == 'pre':
            for k in range(4 if b == B_DROP - 2 else 2):
                add(drums, t0 + k * BEAT, K, .9); kicks.append(t0 + k * BEAT)
        if sec == 'break':
            add(drums, t0, K, .7); kicks.append(t0)
        if sec in ('build', 'drop', 'japan'):
            add(drums, t0 + BEAT, CL, .55); add(drums, t0 + 3 * BEAT, CL, .55)
            for k in range(4): add(drums, t0 + (k + .5) * BEAT, HO, .22)
        if sec in ('intro', 'build', 'drop', 'japan'):
            for k in range(16):
                add(drums, t0 + k * BEAT / 4, HC, (.16 if k % 2 else .1) * (1.0 if sec != 'intro' else .7))
        if sec == 'pre':   # 加速するスネアロール(8分 → 16分 → 32分)
            first = b == B_DROP - 2
            tr_ = 0.0
            while tr_ < BAR - 1e-6:
                half = tr_ >= BAR / 2
                step = (BEAT / 2 if not half else BEAT / 4) if first else (BEAT / 4 if not half else BEAT / 8)
                prog = ((0 if first else BAR) + tr_) / (2 * BAR)
                add(drums, t0 + tr_, SN, .2 + .5 * prog)
                tr_ += step
        # ---- ベース(8分、サイドチェイン) ----
        if sec in ('intro', 'build', 'drop', 'japan'):
            for k in range(8):
                d = BEAT / 2 * .9; f = midi(root - 12 + (12 if (sec == 'drop' and k % 2) else 0))
                tb = tt(d)
                s = (np.sin(2 * np.pi * f * tb) + .45 * lp(saw(f, d), 900)) * env(len(tb), .005, .04)
                add(bass, t0 + k * BEAT / 2, s, .9 if sec != 'intro' else .7)
        if sec == 'break':
            d = BAR; tb = tt(d); f = midi(root - 12)
            add(bass, t0, np.sin(2 * np.pi * f * tb) * env(len(tb), .3, .5), .45)
        # ---- パッド / スーパーソウ ----
        d = BAR + .05
        cut = {'intro': 900, 'build': 1400, 'pre': 2200, 'drop': 5200, 'japan': 3200, 'break': 1600}[sec]
        if sec == 'build': cut = 1100 + 1400 * (b - B_BUILD) / max(1, B_DROP - 2 - B_BUILD)
        voices = 7 if sec == 'drop' else 3
        for side, ch in ((0, -1), (1, 1)):
            sig = np.zeros(int(d * SR), np.float32)
            for m in chord + [chord[0] + 12]:
                for v in range(voices):
                    det = (v - (voices - 1) / 2) * (.006 if voices > 3 else .004) + ch * .002
                    sig += saw(midi(m) * (1 + det), d, rng.random())
            sig = lp(sig, cut) / (voices * 4)
            gain = {'intro': .35, 'build': .45, 'pre': .55, 'drop': .75, 'japan': .55, 'break': .5}[sec]
            add(pad[side], t0, sig * env(len(sig), .01 if sec == 'drop' else .25, .08), gain)
        # ---- リード(アルペジオ) ----
        if sec in ('build', 'drop', 'japan', 'break'):
            pat = [0, 1, 2, 3, 2, 1, 0, 2] * 2
            notes = chord + [chord[0] + 12]
            for k in range(16 if sec != 'break' else 8):
                step = BEAT / 4 if sec != 'break' else BEAT / 2
                m = notes[pat[k] % 4] + (12 if sec in ('drop', 'japan') else 0)
                dd = step * 1.6; tn = tt(dd)
                tone = (np.sign(np.sin(2 * np.pi * midi(m) * tn)) * .35 + np.sin(2 * np.pi * midi(m) * tn)) * np.exp(-tn / .09)
                tone = lp(tone.astype(np.float32), 3500)
                side = k % 2
                g = {'build': .18, 'drop': .26, 'japan': .24, 'break': .16}[sec]
                add(lead[side], t0 + k * step, tone, g); add(lead[1 - side], t0 + k * step, tone, g * .55)
    # ---- ドロップ前のライザーとドロップの衝撃 ----
    rs = (B_DROP - 2) * BAR; rd = DROP_T - rs
    t = tt(rd); k = t / rd
    nz = noise(rd)
    riser = np.zeros(len(t), np.float32); blk = 2400
    for i in range(0, len(t), blk):
        f = 600 + 7000 * k[i] ** 2; riser[i:i + blk] = bp(nz[i:i + blk], f * .7, min(f * 1.4, 20000))
    riser = riser * k ** 1.5 * .6 + sweep(200, 1600, rd) * k ** 2 * .15
    add(fx, rs, riser, 1.0)
    tb = tt(2.0)
    add(fx, DROP_T, (sweep(90, 28, 2.0) * np.exp(-tb / .6) + lp(noise(2.0), 400) * np.exp(-tb / .15) * .5), 1.1)
    # ---- サイドチェイン ----
    sc = np.ones(N, np.float32)
    for kt in kicks:
        s = int(kt * SR); n = int(.28 * SR); e = min(s + n, N)
        sc[s:e] = np.minimum(sc[s:e], 1 - .7 * np.exp(-np.arange(e - s) / SR / .07))
    bass *= sc; pad *= sc; lead *= (.5 + .5 * sc)
    drums = norm(drums) * .8; bass = norm(lp(bass, 4000)) * .55
    pad = norm(pad) * .7; lead = norm(lead) * .5; fx = norm(fx) * .55
    L = drums + bass + pad[0] + reverb(lead[0], .3) + fx
    R = drums + bass + pad[1] + reverb(lead[1], .3, 1.07) + fx
    out = np.stack([L, R])
    # 冒頭は即座に鳴らす(フェードは 30ms)、最後の 1.2 秒でフェードアウトしてループにつなぐ
    out *= env(N, .03, 1.2)
    return norm(out, .9).astype(np.float32)

# ---------------- 効果音 ----------------
def sfx_impact(g):
    d = 1.4; t = tt(d)
    sub = sweep(95, 26, d) * np.exp(-t / .45)
    crack = lp(noise(d), 2500) * np.exp(-t / .05) * .6
    return reverb((sub + crack).astype(np.float32), .2) * g
def sfx_hit(g):
    d = .5; t = tt(d)
    return ((sweep(140, 45, d) * np.exp(-t / .12)) + bp(noise(d), 300, 3000) * np.exp(-t / .03) * .5).astype(np.float32) * g
def sfx_whoosh(g, rev=False):
    d = .4; t = tt(d); k = t / d; nz = noise(d); y = np.zeros_like(nz); blk = 960
    for i in range(0, len(t), blk):
        f = 400 + 5000 * np.sin(np.pi * k[i]) ** 2; y[i:i + blk] = bp(nz[i:i + blk], f * .6, min(f * 1.5, 20000))
    y *= np.sin(np.pi * k) ** 2
    return (y[::-1] if rev else y) * g * .9
def sfx_tick(g):
    d = .05; t = tt(d); return (np.sin(2 * np.pi * 2600 * t) * np.exp(-t / .008)).astype(np.float32) * g * .6
def sfx_pop(g):
    d = .14; t = tt(d); return (sweep(380, 1100, d) * np.exp(-t / .04)).astype(np.float32) * g * .8
def sfx_stamp(g):
    d = .5; t = tt(d)
    return reverb((np.sin(2 * np.pi * 110 * t) * np.exp(-t / .07) + lp(noise(d), 1200) * np.exp(-t / .035) * .9).astype(np.float32), .25) * g
def bell(f, d=1.2):
    t = tt(d); return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (.5 / r ** .5)) for r, a in ((1, 1), (2.76, .4), (5.4, .2))).astype(np.float32)
def sfx_ding(g): return reverb(bell(1568), .3) * g * .5
def sfx_cash(g):
    y = np.zeros(int(1.3 * SR), np.float32); add(y, 0, bell(2093, 1.0), .5); add(y, .09, bell(2637, 1.0), .5)
    add(y, 0, hp(noise(.25), 5000) * np.exp(-tt(.25) / .06), .4); return reverb(y, .3) * g
def sfx_roll(g, dur):
    y = np.zeros(int((dur + .1) * SR), np.float32); t = 0.0
    while t < dur:
        k = t / dur; d = .03; tn = tt(d)
        add(y, t, np.sin(2 * np.pi * (1500 + 1800 * k) * tn) * np.exp(-tn / .006), .5)
        t += lerp(.075, .035, k)
    return y * g
def lerp(a, b, k): return a + (b - a) * k
def sfx_sand(g, dur):
    d = dur; t = tt(d); y = hp(noise(d), 3000) * .08
    clicks = np.zeros(len(t), np.float32); idx = rng.integers(0, len(t), int(d * 900)); clicks[idx] = rng.uniform(-1, 1, len(idx))
    y = y + bp(clicks, 2000, 9000) * .9
    return (y * env(len(t), .15, .3)).astype(np.float32) * g * .6
def sfx_uplift(g, dur):
    t = tt(dur); k = t / dur; return (sweep(300, 2400, dur) * k ** 2 * .4 + hp(noise(dur), 4000) * k ** 2 * .3).astype(np.float32) * g
def sfx_shimmer(g):
    y = np.zeros(int(1.2 * SR), np.float32)
    for i, m in enumerate([81, 84, 88, 93]): add(y, i * .05, bell(midi(m), .9), .3)
    return reverb(y, .4) * g
def sfx_alarm(g, dur):
    t = tt(dur); f = np.where((t // .25) % 2 == 0, 880, 660)
    s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)).astype(np.float32)
    return lp(s, 2500) * env(len(t), .02, .3) * g * .22
def sfx_glitch(g):
    d = .14; t = tt(d); sq = np.sign(np.sin(2 * np.pi * 150 * t * (1 + 3 * rng.random(len(t)) * (t > .05))))
    crush = np.round(noise(d) * 3) / 3
    return lp((sq * .4 + crush * .3).astype(np.float32), 6000) * env(len(t), .002, .03) * g * .7
def sfx_zap(g):
    d = .45; t = tt(d); return reverb((sweep(2400, 180, d) * np.exp(-t / .15) + .3 * sweep(4800, 360, d) * np.exp(-t / .1)).astype(np.float32), .3) * g * .5
def sfx_drop(g):
    d = .5; t = tt(d); y = np.zeros(len(t), np.float32)
    blip = sweep(1300, 320, .12) * np.exp(-tt(.12) / .04); add(y, 0, blip, .5)
    add(y, .12, np.sin(2 * np.pi * 80 * tt(.3)) * np.exp(-tt(.3) / .08), .9)
    return y * g

def sfx():
    evs = json.load(open(os.path.join(OUT, 'events.json'), encoding='utf-8'))
    y = np.zeros(N, np.float32)
    for e in evs:
        typ, g, t0 = e['type'], e['g'], e['t']; dur = e.get('dur', .5)
        sig = {
            'impact': lambda: sfx_impact(g), 'hit': lambda: sfx_hit(g), 'whoosh': lambda: sfx_whoosh(g),
            'swoosh': lambda: sfx_whoosh(g, True), 'tick': lambda: sfx_tick(g), 'pop': lambda: sfx_pop(g),
            'stamp': lambda: sfx_stamp(g), 'ding': lambda: sfx_ding(g), 'cash': lambda: sfx_cash(g),
            'roll': lambda: sfx_roll(g, dur), 'sand': lambda: sfx_sand(g, dur), 'uplift': lambda: sfx_uplift(g, dur),
            'shimmer': lambda: sfx_shimmer(g), 'alarm': lambda: sfx_alarm(g, dur), 'glitch': lambda: sfx_glitch(g),
            'zap': lambda: sfx_zap(g), 'drop': lambda: sfx_drop(g),
        }[typ]()
        add(y, t0, np.asarray(sig, np.float32))
    return y

# ---------------- ミックス ----------------
def read_wav(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x if w.getnchannels() == 1 else x.reshape(-1, w.getnchannels()).T
def write_wav(p, x):
    x = np.atleast_2d(x); ch = x.shape[0]
    with wave.open(p, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x.T, -1, 1) * 32767).astype(np.int16).tobytes())

def main():
    music = bgm(); write_wav(os.path.join(OUT, 'bgm.wav'), music)
    fxs = sfx(); write_wav(os.path.join(OUT, 'sfx.wav'), norm(fxs, .9))
    voice = read_wav(os.path.join(OUT, 'narration.wav'))
    voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
    # ナレーションの包絡でダッキング(アタック 30ms / リリース 400ms)
    hop = SR // 100
    rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
    e = np.zeros_like(rms)
    for i, v in enumerate(rms):
        p = e[i - 1] if i else 0.0
        e[i] = max(v, p * .975) if v < p else p + (v - p) * .5
    e = np.pad(np.repeat(e, hop), (0, N))[:N]
    speech = np.clip(e / .06, 0, 1)
    BGM_OPEN, BGM_UNDER = .55, .13
    gain = BGM_OPEN - (BGM_OPEN - BGM_UNDER) * speech
    # 声の帯域(1〜4kHz)とぶつかる BGM の中高域を、発話中だけさらに少し削る
    mid = np.stack([bp(music[0], 900, 4000), bp(music[1], 900, 4000)])
    music = music - mid * .5 * speech
    mix = music * gain + norm(fxs, 1.0) * .42 * (1 - .55 * speech) + voice[None, :] * 1.0
    mix = mix / max(1.0, np.max(np.abs(mix)) / .97)
    write_wav(os.path.join(OUT, 'mix.wav'), mix)
    src = os.path.join(OUT, 'video_silent.mp4'); dst = os.path.join(OUT, 'semiconductor_short.mp4')
    # 2パスの loudnorm で -14 LUFS(YouTube の基準)に合わせる
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', os.path.join(OUT, 'mix.wav'), '-af',
                        'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', os.path.join(OUT, 'mix.wav'),
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af, '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', '-movflags', '+faststart', dst], check=True)
    print('wrote', dst)

if __name__ == '__main__':
    main()
