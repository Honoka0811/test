# -*- coding: utf-8 -*-
"""BGM(自作のポップ曲)と効果音を numpy だけで合成し、ナレーションとミックスして動画に載せる。

  入力: timeline.json, output/voice.wav, output/video_silent.mp4
  出力: output/bgm.wav, output/sfx.wav, output/mix.wav, output/baito_ranking.mp4

使い方: python3 audio.py            (--audio-only で動画への合成を省略)
- BGM: 128BPM・Cメジャー(C-G-Am-F)。キック/クラップ/ハット+オクターブベース+裏打ちコード+マリンバ風メロディ。
  第1位発表(r1 の頭)で曲を頭から鳴らし直す(render.html の beatPulse もこれに合わせて脈打つ)
- 効果音: シュッ(場面転換)、ドン(順位バッジ)、ジャン(職種発表)、ポンッ(メリット)、星のカチカチ、
  ドラムロール+ライザー、クラッシュ+ファンファーレ、コイン、キラキラ
- 外部音源は使っていないので権利表記は不要
"""
import os, sys, json, wave, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
BPM = 128
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(20261128)

# render.html の JOBS.meters と同じ値(星の数 → 星のカチカチ音の回数)
METERS = {'r5': [4, 2, 5], 'r4': [4, 2, 4], 'r3': [5, 3, 3], 'r2': [5, 3, 4], 'r1': [5, 5, 5]}


# ------------------------------------------------------------------ utils
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def add(buf, x, t, gain=1.0):
    s = int(round(t * SR))
    if s < 0:
        x, s = x[-s:], 0
    if s >= len(buf):
        return
    e = min(len(buf), s + len(x))
    buf[s:e] += x[:e - s] * gain


def fft_filter(x, lo=0.0, hi=0.0, order=2):
    n = len(x)
    N = 1 << int(np.ceil(np.log2(n + 1)))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1 / SR)
    H = np.ones_like(f)
    if lo:
        H *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    if hi:
        H *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * H, N)[:n]


def sweep_filter(x, lo_fn, hi_fn, frame=1024):
    """フレームごとにカットオフを変えるバンドパス(Hann 窓 50% オーバーラップ加算)"""
    hop = frame // 2
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(frame) / frame)
    f = np.fft.rfftfreq(frame, 1 / SR)
    out = np.zeros(len(x) + frame)
    for s in range(0, len(x), hop):
        seg = x[s:s + frame]
        seg = np.pad(seg, (0, frame - len(seg))) * win
        tc = (s + frame / 2) / SR
        H = 1 / np.sqrt(1 + (lo_fn(tc) / np.maximum(f, 1e-3)) ** 4) / np.sqrt(1 + (f / hi_fn(tc)) ** 4)
        out[s:s + frame] += np.fft.irfft(np.fft.rfft(seg) * H, frame)
    return out[:len(x)]


def noise(dur):
    return rng.standard_normal(int(dur * SR))


def norm(x, peak=1.0):
    return x * (peak / (np.max(np.abs(x)) or 1))


# ------------------------------------------------------------------ instruments
def kick():
    t = tt(0.42)
    f = 46 + 120 * np.exp(-t / 0.032)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.17)
    click = fft_filter(noise(0.42) * np.exp(-t / 0.004), lo=1800) * 0.35
    return body + click


def clap():
    t = tt(0.32)
    e = np.zeros_like(t)
    for d in (0.0, 0.010, 0.021):
        e += (t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.007)
    e += (t >= 0.021) * np.exp(-np.clip(t - 0.021, 0, None) / 0.12) * 0.8
    return fft_filter(noise(0.32) * e, lo=900, hi=5200) * 1.4


def hat(open_=False):
    d = 0.26 if open_ else 0.08
    t = tt(d)
    return fft_filter(noise(d), lo=7500) * np.exp(-t / (0.075 if open_ else 0.018)) * 0.5


def bass(m, dur):
    t = tt(dur)
    f = mtof(m)
    x = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 9)) * 0.55 + 0.7 * np.sin(2 * np.pi * f * t)
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.28) * np.clip((dur - t) / 0.015, 0, 1)
    return x * env


def pluck(notes, dur=0.24):
    t = tt(dur)
    x = np.zeros_like(t)
    for m in notes:
        f = mtof(m)
        for k in range(1, 12):
            if f * k > 9000:
                break
            x += np.exp(-t * (7 + 3.5 * k)) * np.sin(2 * np.pi * f * k * t + k) / k
    return x * np.minimum(1, t / 0.003)


def pad(notes, dur):
    t = tt(dur)
    x = np.zeros_like(t)
    for m in notes:
        f = mtof(m)
        for det in (-0.12, 0.12):
            ff = f * 2 ** (det / 12)
            x += np.sin(2 * np.pi * ff * t) + 0.3 * np.sin(4 * np.pi * ff * t)
    env = np.minimum(1, t / 0.12) * np.clip((dur - t) / 0.2, 0, 1)
    return x * env / len(notes)


def bell(m, dur=0.55):
    """マリンバ/グロッケン風(FM)"""
    t = tt(dur)
    f = mtof(m)
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 2.0 * np.exp(-t / 0.1)
    x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t / 0.26)
    x += 0.3 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.05)
    return x * np.minimum(1, t / 0.002)


# C - G - Am - F
PROG = [([60, 64, 67, 72], 36), ([59, 62, 67, 71], 43), ([60, 64, 69, 72], 45), ([60, 65, 69, 72], 41)]
MEL = [[76, 79, None, 76, 74, 72, 74, 76],
       [74, None, 71, 74, 79, None, 74, None],
       [72, 76, 81, None, 79, 76, 72, 76],
       [77, None, 81, 79, 77, 76, 74, None]]
MEL_END = [77, None, 81, 79, 76, None, 72, None]


def bgm(dur, big=False):
    n = int(dur * SR) + SR
    drums, low, mid, lead = (np.zeros(n) for _ in range(4))
    K, C, Hc, Ho = kick(), clap(), hat(), hat(True)
    for b in range(int(np.ceil(dur / BAR)) + 1):
        t0 = b * BAR
        chord, root = PROG[b % 4]
        for q in range(4):
            add(drums, K, t0 + q * BEAT)
            add(mid, pluck(chord), t0 + q * BEAT + BEAT / 2, 0.55)
        for q in (1, 3):
            add(drums, C, t0 + q * BEAT, 0.55)
        for e in range(8):
            add(drums, Ho if e % 2 else Hc, t0 + e * BEAT / 2, 0.55 if e % 2 else 0.4)
            add(low, bass(root + (12 if e % 2 else 0), BEAT / 2 * 0.9), t0 + e * BEAT / 2, 0.42)
        if big:  # 第1位以降は16分のハットを足して疾走感アップ
            for e in range(16):
                if e % 2:
                    add(drums, Hc, t0 + e * BEAT / 4, 0.22)
        add(mid, pad(chord, BAR), t0, 0.10)
        mel = MEL_END if (b % 8 == 7) else MEL[b % 4]
        for e, m in enumerate(mel):
            if m:
                add(lead, bell(m), t0 + e * BEAT / 2, 0.30)
                if big:
                    add(lead, bell(m + 12), t0 + e * BEAT / 2, 0.10)
    # キックに合わせたサイドチェイン(ポップスらしい「うねり」)
    ph = (np.arange(n) / SR) % BEAT
    sc = 1 - 0.6 * np.exp(-ph / 0.09)
    out = drums * 0.85 + (low + mid) * sc + lead
    return out[:int(dur * SR)]


# ------------------------------------------------------------------ sfx
def whoosh(d=0.5):
    t = tt(d)
    x = noise(d)
    c = lambda tc: 300 + 5000 * np.sin(np.pi * min(tc / d, 1)) ** 2
    y = sweep_filter(x, lambda tc: c(tc) * 0.5, lambda tc: c(tc) * 1.8)
    return norm(y * np.sin(np.pi * t / d) ** 2, 0.55)


def slam():
    t = tt(0.8)
    f = 38 + 90 * np.exp(-t / 0.05)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.25)
    crack = fft_filter(noise(0.8) * np.exp(-t / 0.03), lo=200, hi=6000) * 0.5
    return norm(boom + crack, 0.9)


def stinger(notes=(60, 64, 67, 72, 76), d=0.9):
    """ジャン!(明るいコードのヒット)"""
    t = tt(d)
    x = np.zeros_like(t)
    for m in notes:
        f = mtof(m)
        for k in range(1, 14):
            if f * k > 11000:
                break
            x += np.sin(2 * np.pi * f * k * t + k * 0.7) / k * np.exp(-t * (3 + k * 0.8))
    x *= np.minimum(1, t / 0.004)
    cym = fft_filter(noise(d), lo=5000) * np.exp(-t / 0.35) * 0.25
    return norm(x / len(notes) + cym, 0.8)


def popfx(f0=520, f1=1300, d=0.12):
    t = tt(d)
    f = f0 + (f1 - f0) * np.minimum(1, t / 0.05)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) * np.minimum(1, t / 0.002) * 0.7


def tick(k):
    t = tt(0.09)
    f = 1500 * 2 ** (k / 12)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.02) * 0.35


def coin():
    t1, t2 = tt(0.07), tt(0.45)
    sq = lambda f, t: np.sign(np.sin(2 * np.pi * f * t))
    a = sq(988, t1) * 0.3
    b = sq(1319, t2) * np.exp(-t2 / 0.12) * 0.3
    return fft_filter(np.concatenate([a, b]), hi=7000)


def sparkle_fx():
    out = np.zeros(int(1.0 * SR))
    for i, m in enumerate([84, 88, 91, 96, 100]):
        add(out, bell(m, 0.5), i * 0.045, 0.35)
    return out


def drumroll(d):
    out = np.zeros(int((d + 0.3) * SR))
    t = 0.0
    while t < d:
        k = t / d
        tn = tt(0.09)
        hit = fft_filter(noise(0.09), lo=1200, hi=7000) * np.exp(-tn / 0.03) + 0.5 * np.sin(2 * np.pi * 190 * tn) * np.exp(-tn / 0.03)
        add(out, hit, t, 0.25 + 0.75 * k ** 1.5)
        t += 1 / (13 + 20 * k)
    return norm(out, 0.75)


def riser(d):
    t = tt(d)
    y = sweep_filter(noise(d), lambda tc: 200 + 3000 * (tc / d) ** 2, lambda tc: 600 + 9000 * (tc / d) ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(180 * 2 ** (2.2 * t / d)) / SR) * 0.3
    return norm((y + tone) * (t / d) ** 2, 0.6)


def crash(d=2.6):
    t = tt(d)
    return norm(fft_filter(noise(d), lo=4200) * np.exp(-t / 0.9) * np.minimum(1, t / 0.002), 0.7)


def fanfare():
    """パッ・パーン!(金管風)"""
    out = np.zeros(int(2.2 * SR))
    for st, dur, notes in ((0.0, 0.13, (67, 71, 74)), (0.17, 1.5, (72, 76, 79, 84))):
        t = tt(dur)
        x = np.zeros_like(t)
        for m in notes:
            f = mtof(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.3))
            ph = 2 * np.pi * np.cumsum(f) / SR
            for k in range(1, 10):
                x += np.sin(k * ph) / k ** 1.1
        env = np.minimum(1, t / 0.025) * np.clip((dur - t) / 0.12, 0, 1) * (np.exp(-t / 1.2) * 0.7 + 0.3)
        add(out, x * env / len(notes), st)
    return norm(out, 0.8)


# ------------------------------------------------------------------ mastering
def _smooth_gain(g, att, rel):
    out = np.empty_like(g)
    y = 1.0
    for i, v in enumerate(g):
        y = v if v < y else y + (v - y) * rel   # 下げるのは即座、戻すのはゆっくり
        out[i] = y
    return out


def master(x, comp_thr_db=-18, ratio=3.0, lim_thr=0.33, ceil=0.80):
    """スマホで聞きやすいよう軽くコンプ → 先読みリミッター → -1dBFS に揃える。
    (アップロード時の -14 LUFS 正規化でピークが潰れないよう、ピークとラウドネスの差を詰めておく)"""
    blk = SR // 400                                  # 2.5ms ブロック
    n = len(x) // blk * blk
    x = x[:n]
    # コンプレッサー(30ms RMS)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(SR * 3 // 100) / (SR * 3 // 100), mode='same')).reshape(-1, blk).max(axis=1)
    db = 20 * np.log10(np.maximum(rms, 1e-6))
    over = np.maximum(db - comp_thr_db, 0)
    g = 10 ** (-over * (1 - 1 / ratio) / 20)
    g = _smooth_gain(g, 0, 0.02)
    x = x * np.repeat(g, blk)
    x = x / np.max(np.abs(x))
    # リミッター(5ms 先読み)
    pk = np.abs(x).reshape(-1, blk).max(axis=1)
    pk = np.max(np.stack([np.roll(pk, -k) for k in range(3)]), axis=0)
    g = np.minimum(1, lim_thr / np.maximum(pk, 1e-9))
    g = _smooth_gain(g, 0, 0.01)
    g = np.convolve(g, np.ones(3) / 3, mode='same')
    ge = np.interp(np.arange(n), np.arange(len(g)) * blk + blk / 2, g)
    y = x * ge
    y = np.clip(y / lim_thr, -1, 1) * ceil
    return y


# ------------------------------------------------------------------ build
def main():
    tl = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))
    total = tl['duration']
    SC = {s['id']: s for s in tl['scenes']}
    N = int(total * SR)

    # ---- BGM
    music = np.zeros(N + SR)
    drum_t0, r1_t0 = SC['drum']['t0'], SC['r1']['t0']
    a = bgm(drum_t0 + 0.6)
    fa = np.ones_like(a)
    i0, i1 = int((drum_t0 - 0.05) * SR), int((drum_t0 + 0.45) * SR)
    fa[i0:i1] = np.linspace(1, 0, i1 - i0)
    fa[i1:] = 0
    add(music, a * fa, 0)
    b = bgm(total - r1_t0 + 0.1, big=True)
    fo = int(1.8 * SR)
    b[-fo:] *= np.linspace(1, 0, fo) ** 2
    add(music, b, r1_t0)
    music = norm(music[:N], 0.9)

    # ---- SFX
    sfx = np.zeros(N + 3 * SR)
    W, SL, ST, P = whoosh(), slam(), stinger(), popfx()
    # オープニング
    add(sfx, ST, 0.0, 0.7)
    add(sfx, slam(), 0.0, 0.5)
    for i in range(3):
        add(sfx, popfx(400 + i * 120, 1000 + i * 200), 0.02 + i * 0.1, 0.5)
    add(sfx, sparkle_fx(), 0.55, 0.6)
    add(sfx, stinger((65, 69, 72, 77, 81)), SC['intro']['marks'].get('top5', 3), 0.6)
    for sid in ('r5', 'r4', 'r3', 'r2', 'r1'):
        s, m = SC[sid], SC[sid]['marks']
        if sid != 'r1':
            add(sfx, W, s['t0'] - 0.25, 0.8)
        add(sfx, SL, s['t0'] + 0.08, 0.75)
        if sid == 'r1':
            add(sfx, crash(), s['t0'], 0.8)
            add(sfx, fanfare(), s['t0'] + 0.05, 0.75)
            add(sfx, sparkle_fx(), s['t0'] + 0.35, 0.6)
        else:
            add(sfx, ST, m['name'], 0.6)
        tm = m['meters']
        for ci, v in enumerate(METERS[sid]):
            for k in range(v):
                add(sfx, tick(k + ci * 2), tm + 0.15 + ci * 0.12 + k * 0.06, 0.55)
        for i in range(4):
            if f'p{i}' in m:
                add(sfx, P, m[f'p{i}'], 0.7)
        if 'money' in m:
            add(sfx, coin(), m['money'], 0.6)
            add(sfx, coin(), m['money'] + 0.16, 0.45)
    # ドラムロール(暗転 → 第1位)
    d0 = drum_t0
    add(sfx, slam(), d0, 0.45)
    add(sfx, drumroll(r1_t0 - d0 - 0.3), d0 + 0.3, 0.75)
    add(sfx, riser(r1_t0 - d0 - 0.2), d0 + 0.2, 0.35)
    # エンディング
    so = SC['outro']
    add(sfx, W, so['t0'] - 0.25, 0.8)
    for i in range(5):
        add(sfx, popfx(500 + i * 90, 1100 + i * 150), so['t0'] + 0.15 + (4 - i) * 0.09, 0.45)
    if 'cta' in so['marks']:
        add(sfx, sparkle_fx(), so['marks']['cta'], 0.65)
        add(sfx, P, so['marks']['cta'], 0.7)
    sfx = sfx[:N]

    # ---- voice + ducking
    with wave.open(os.path.join(OUT, 'voice.wav')) as w:
        voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
    hop = SR // 50
    rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(rms)
    for i, v in enumerate(rms):
        env[i] = max(v, (env[i - 1] if i else 0) * 0.95)      # リリース ≈ 0.4 秒
    env = np.pad(np.repeat(env, hop), (0, N - len(rms) * hop))
    speech = np.clip(env / 0.08, 0, 1)
    # 発話中の RMS を基準に BGM の量を決める(発話中 -12dB / 無音時 -5dB)
    v_rms = np.sqrt(np.mean(voice[speech > 0.5] ** 2))
    m_rms = np.sqrt(np.mean(music ** 2))
    g_speech = v_rms / m_rms * 10 ** (-12 / 20)
    g_silent = v_rms / m_rms * 10 ** (-5 / 20)
    gain = g_silent - (g_silent - g_speech) * speech
    k = SR // 12
    gain = np.convolve(gain, np.ones(k) / k, mode='same')
    s_gain = v_rms / (np.sqrt(np.mean(sfx[np.abs(sfx) > 1e-4] ** 2)) or 1) * 10 ** (-6 / 20)
    mixed = voice + music * gain + sfx * s_gain
    peak = np.max(np.abs(mixed))
    mixed = master(mixed / peak)
    print(f'BGM gain speech {g_speech:.3f} / silent {g_silent:.3f}, sfx {s_gain:.3f}, peak {peak:.2f}')

    def wr(name, x):
        with wave.open(os.path.join(OUT, name), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    wr('bgm.wav', music * 0.9)
    wr('sfx.wav', norm(sfx, 0.9))
    wr('mix.wav', mixed)

    src = os.path.join(OUT, 'video_silent.mp4')
    dst = os.path.join(OUT, 'baito_ranking.mp4')
    if os.path.exists(src) and '--audio-only' not in sys.argv:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', os.path.join(OUT, 'mix.wav'),
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
        print('wrote', dst)
    else:
        print('video_silent.mp4 が無いので音声だけ書き出しました(先に node capture.js を実行)')


if __name__ == '__main__':
    main()
