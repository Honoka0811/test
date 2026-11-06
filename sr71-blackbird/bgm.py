# -*- coding: utf-8 -*-
"""シネマティック・トレーラー風 BGM + 効果音をプログラムで合成する(外部音源なし・権利フリー)。
D マイナー / 128BPM。timeline.json のシーン切り替えに合わせて
インパクト・ブラーム・ライザー・ウーシュを打ち、曲の展開(緊張→疾走→溜め→爆発→余韻)を作る。
generate(timeline) -> (music[N,2], sfx[N,2])  ※ どちらも 48kHz ステレオ float32
単体実行: python3 bgm.py  → output/bgm.wav, output/sfx.wav
"""
import json, os, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 128
BEAT = 60 / BPM
RNG = np.random.default_rng(71)


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def T(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], 'band', fs=SR, output='sos'), x)
def noise(d): return RNG.standard_normal(int(d * SR))
def saw(f, t): return 2 * ((f * t) % 1) - 1


def put(buf, t0, sig, gain=1.0, pan=0.0):
    """ステレオバッファに mono 信号を等パワーパンで加算"""
    s = int(t0 * SR)
    if s >= len(buf): return
    sig = sig[:len(buf) - s]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[s:s + len(sig), 0] += sig * gain * l * 1.414
    buf[s:s + len(sig), 1] += sig * gain * r * 1.414


# ---------------- 音色 ----------------
def kick(d=0.45):
    t = T(d)
    f = 45 + 110 * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    click = lp(noise(d), 3000) * np.exp(-t / 0.004) * 0.5
    return np.tanh(1.6 * (body + click))


def snare(d=0.3):
    t = T(d)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    nz = bp(noise(d), 1200, 9000) * np.exp(-t / 0.08)
    return 0.6 * tone + 0.9 * nz


def hat(d=0.06, open_=False):
    t = T(0.25 if open_ else d)
    return hp(noise(len(t) / SR), 7000) * np.exp(-t / (0.08 if open_ else 0.015))


def tom(f0=110, d=0.6):
    t = T(d)
    f = f0 * (1 + 0.6 * np.exp(-t / 0.05))
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22))


def bass_note(n, d):
    t = T(d)
    f = midi(n)
    x = saw(f, t) + 0.5 * saw(f * 1.006, t) + 0.6 * np.sin(2 * np.pi * f / 2 * t)
    env = np.minimum(1, t / 0.004) * np.exp(-t / (d * 0.9))
    w = np.exp(-t / 0.06)
    return np.tanh(1.5 * (lp(x, 1500) * w + lp(x, 600) * (1 - w)) * env)


def stab(notes, d):
    """スタッカート・ストリングス風の和音"""
    t = T(d)
    x = sum(saw(midi(n) * (1 + dt), t) for n in notes for dt in (-0.003, 0.003))
    env = np.minimum(1, t / 0.006) * np.exp(-t / 0.09)
    return lp(x, 3200) * env / len(notes)


def braam(root=38, d=3.5):
    """トレーラーの「ブォーン」: 低い金管風の歪んだ和音、フィルタが開いて閉じる"""
    t = T(d)
    x = np.zeros_like(t)
    for n, g in ((root - 12, 1.0), (root, 0.9), (root + 7, 0.6), (root + 12, 0.5), (root + 15, 0.3)):
        for dt in (-0.004, 0, 0.005):
            x += g * saw(midi(n) * (1 + dt), t)
    # フィルタを時間変化させる代わりに、明暗 2 本をクロスフェード
    bright, dark = lp(x, 2400, 4), lp(x, 260, 4)
    w = np.exp(-t / 0.5)
    y = np.tanh(0.5 * (bright * w + dark * (1 - w)))
    env = np.minimum(1, t / 0.03) * np.exp(-t / (d * 0.45))
    return y * env


def impact(d=3.0):
    t = T(d)
    f = 28 + 70 * np.exp(-t / 0.12)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    crack = lp(noise(d), 5000) * np.exp(-t / 0.05)
    tail = lp(noise(d), 900) * np.exp(-t / 0.7) * 0.4
    return np.tanh(1.8 * boom + 0.7 * crack + tail)


def riser(d):
    t = T(d)
    p = t / d
    f = 180 * (12 ** p)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    nz = hp(noise(d), 400) * (p ** 2)
    return (tone + nz * 0.6) * (p ** 2.2)


def whoosh(d=0.7, rev=False):
    t = T(d)
    p = t / d
    env = np.sin(np.pi * p) ** 2
    x = bp(noise(d), 300, 4000) * env
    return x[::-1] if rev else x


def ping():
    t = T(1.2)
    return (np.sin(2 * np.pi * 1320 * t) + 0.3 * np.sin(2 * np.pi * 2640 * t)) * np.exp(-t / 0.25)


def alarm(d=0.18):
    t = T(d)
    return np.sign(np.sin(2 * np.pi * 880 * t)) * 0.3 * np.minimum(1, (d - t) / 0.02)


def tick():
    t = T(0.03)
    return hp(noise(0.03), 3000) * np.exp(-t / 0.004)


def jet(d=2.2):
    """ジェット機の通過音(ドップラー風に帯域を上下させたノイズ)"""
    t = T(d)
    p = t / d
    lo = lp(noise(d), 700)
    hi = hp(noise(d), 2500)
    env = np.exp(-((p - 0.45) / 0.22) ** 2)
    return (lo * 1.2 + hi * 0.5 * env) * env


def sub_drop(d=1.5):
    t = T(d)
    f = 70 * np.exp(-t / 0.6) + 25
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.6)


def reverb(x, mix=0.25):
    """簡易ステレオリバーブ(フィードバックコム ×4 を左右で別ディレイ)"""
    out = np.zeros_like(x)
    for ch, ds in ((0, (1557, 1913, 2333, 2687)), (1, (1617, 1999, 2203, 2791))):
        wet = np.zeros(len(x))
        for d in ds:
            y = x[:, ch].copy()
            for s in range(d, len(y), d):
                e = min(s + d, len(y))
                y[s:e] += 0.72 * y[s - d:e - d]
            wet += y
        out[:, ch] = lp(wet / 4, 6000)
    return (1 - mix) * x + mix * out


# ---------------- 曲 ----------------
PROG = [(38, [62, 65, 69]), (34, [62, 65, 70]), (31, [62, 67, 70]), (33, [61, 64, 69])]  # Dm Bb Gm A


def generate(tl):
    total = tl['duration']
    N = int(total * SR) + SR
    music = np.zeros((N, 2)); sfx = np.zeros((N, 2))
    sc = {s['id']: s for s in tl['scenes']}
    t_reveal = sc['reveal']['start']
    zero = sc['ending']['chunks'][1]['start']           # 「ゼロ」
    t_drop = zero - 0.9                                  # 直前で全部止めて溜める
    t_cta = sc['ending']['chunks'][2]['start']

    # --- 0:00 冒頭: 開始と同時にインパクト(最初の1秒で掴む)
    put(music, 0.0, impact(), 0.9)
    put(music, 0.0, braam(38, 3.0), 0.55)
    # 冒頭の緊張: 低いドローン + 時計の秒針のようなチック + 心拍キック
    d = t_reveal
    t = T(d)
    drone = lp(saw(midi(26), t) + saw(midi(26) * 1.01, t), 200) * np.minimum(1, t / 0.5) * 0.35
    put(music, 0.0, drone, 0.8)
    for k in range(int(d / (BEAT / 2))):
        put(music, k * BEAT / 2, tick(), 0.25, pan=0.4 if k % 2 else -0.4)
    for k in range(int(d / BEAT)):
        if k % 2 == 0 and k > 1:
            put(music, k * BEAT, kick(), 0.45)
    put(music, sc['hook']['chunks'][1]['start'] - 0.2, riser(t_reveal - sc['hook']['chunks'][1]['start'] + 0.2), 0.6)

    # --- 本編: リビール以降、ドロップ直前まで 128BPM で疾走
    beats = int((t_drop - t_reveal) / BEAT)
    for b in range(beats):
        tb = t_reveal + b * BEAT
        bar, beat = divmod(b, 4)
        root, chord = PROG[(bar // 1) % 4]
        inten = min(1.0, 0.55 + b / 64)                   # 徐々に厚く
        put(music, tb, kick(), 0.95)
        if beat in (1, 3):
            put(music, tb, snare(), 0.45 * inten, pan=0.05)
        for s16 in range(4):                               # 16 分のベース・オスティナート
            put(music, tb + s16 * BEAT / 4, bass_note(root + (12 if s16 == 2 else 0), BEAT / 4), 0.33)
            put(music, tb + s16 * BEAT / 4, hat(), (0.16 if s16 % 2 else 0.09) * inten, pan=0.3)
        for s8 in range(2):                                # 8 分のストリングス・スタブ
            put(music, tb + s8 * BEAT / 2, stab(chord, BEAT / 2), 0.32 * inten, pan=-0.35 if s8 else 0.35)
        if bar % 4 == 3 and beat == 3:                     # 4 小節ごとのタムフィル
            for j, f0 in enumerate((140, 120, 100, 80)):
                put(music, tb + j * BEAT / 4, tom(f0), 0.5, pan=-0.5 + j / 3)
    # ブレイク: 拍を止めてライザーだけを残す
    put(music, t_drop - 0.1, riser(zero - t_drop + 0.1), 0.85)
    put(sfx, zero - 0.35, whoosh(0.35, rev=True), 0.6)

    # --- 「ゼロ」: 最大のインパクト → 余韻のパッドで CTA
    put(music, zero, impact(4.0), 1.1)
    put(music, zero, braam(38, 4.5), 0.75)
    put(music, zero, sub_drop(2.0), 0.6)
    t = T(total - t_cta + 1)
    pad = sum(lp(saw(midi(n) * (1 + dt), t), 900) for n in (50, 57, 62, 65) for dt in (-0.004, 0.004)) / 8
    put(music, t_cta - 0.4, pad * np.minimum(1, t / 0.6), 0.45)
    for k in range(int((total - t_cta) / BEAT)):
        put(music, t_cta + k * BEAT, kick(), 0.35 if k % 2 == 0 else 0.0)

    # --- シーン切り替えのヒット(リビール以降の各カット)
    for s in tl['scenes'][1:]:
        if s['id'] == 'ending':
            put(music, s['start'], impact(1.8), 0.55)
            continue
        put(sfx, s['start'] - 0.35, whoosh(0.45), 0.5, pan=RNG.uniform(-0.4, 0.4))
        put(music, s['start'], impact(2.0), 0.8 if s['id'] == 'reveal' else 0.5)
    put(music, t_reveal, braam(38, 3.0), 0.6)

    # --- シーン固有の効果音
    h = sc['hook']['start']
    for k in range(4):
        put(sfx, h + 0.3 + k * 1.1, ping(), 0.18, pan=-0.2)          # レーダー
    for k in range(6):
        put(sfx, sc['hook']['chunks'][1]['start'] + k * 0.32, alarm(), 0.10)  # ロックオン警報
    e = sc['escape']['start']
    put(sfx, e + 0.2, whoosh(1.6), 0.6, pan=-0.5)                    # ミサイル発射
    put(sfx, e + 0.5, jet(2.4), 0.45, pan=0.3)
    put(sfx, sc['speed']['start'] + 0.3, jet(2.0), 0.55, pan=-0.3)   # 加速
    put(sfx, sc['titanium']['chunks'][1]['start'] - 0.05, impact(1.2) * 0.5, 0.6)  # 「敵国ソ連」で判子

    music = reverb(music, 0.18)
    sfx = reverb(sfx, 0.25)
    # 全体フェード
    fade = np.ones(N); fo = int(1.2 * SR); end = int(total * SR)
    fade[end - fo:end] = np.linspace(1, 0, fo); fade[end:] = 0
    music *= fade[:, None]; sfx *= fade[:, None]
    music /= np.max(np.abs(music)) + 1e-9
    sfx /= np.max(np.abs(sfx)) + 1e-9
    return music[:end].astype(np.float32), sfx[:end].astype(np.float32)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(x.shape[1] if x.ndim == 2 else 1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    tl = json.load(open(os.path.join(here, 'output', 'timeline.json'), encoding='utf-8'))
    m, s = generate(tl)
    write_wav(os.path.join(here, 'output', 'bgm.wav'), m * 0.9)
    write_wav(os.path.join(here, 'output', 'sfx.wav'), s * 0.9)
    print('wrote output/bgm.wav, output/sfx.wav', f'{len(m) / SR:.1f}s')
