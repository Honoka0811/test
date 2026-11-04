# -*- coding: utf-8 -*-
"""
和風シネマティックBGM（オリジナル合成・著作権フリー）

日本の絶景・観光ランキング動画の定番である「和風×壮大」系の曲。
- 琴風の分散和音（カープラス・ストロング合成）
- 尺八風の笛メロディ（ビブラート＋息の音）
- ストリングスのパッドと低弦
- 和太鼓のグルーヴ
- ホールのような残響
構成: 導入(フック) → 本編(カウントダウン) → ため(第1位直前) → クライマックス(第1位) → 余韻
"""
import functools

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

SR = 44100
BPM = 88
BEAT = 60 / BPM
BAR = BEAT * 4


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


# ---------------------------------------------------------------- 音源
@functools.lru_cache(maxsize=None)
def koto(m, dur=2.2, bright=1.0):
    """琴風の撥弦音（Karplus-Strong）"""
    f = midi(m)
    n = int(dur * SR)
    N = int(SR / f)
    rng = np.random.default_rng(m)
    exc = np.zeros(n)
    burst = rng.uniform(-1, 1, N)
    burst = lp(burst, 2500 + 3000 * bright)
    exc[:N] = burst
    g = 0.997
    a = np.zeros(N + 2)
    a[0] = 1
    a[N] = -0.5 * g
    a[N + 1] = -0.5 * g
    y = lfilter([1.0], a, exc)
    # 撥の当たり（アタック感）
    t = np.arange(n) / SR
    y += np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 25) * 0.25
    return y / (np.max(np.abs(y)) + 1e-9)


def flute(m, dur, rng=np.random.default_rng(11)):
    """尺八風の笛"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi(m)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.35) / 0.4, 0, 1)
    bend = 1 - 0.02 * np.exp(-t * 12)  # 下からしゃくり上げる
    ph = 2 * np.pi * np.cumsum(f * vib * bend) / SR
    tone = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    breath = bp(rng.normal(0, 1, n), f * 0.8, min(f * 4, 9000)) * 0.35
    env = np.clip(t / 0.12, 0, 1) * np.clip((dur - t) / 0.35, 0, 1)
    env *= 0.85 + 0.15 * np.sin(np.pi * np.clip(t / dur, 0, 1))
    return (tone + breath * (0.6 + 0.4 * np.exp(-t * 4))) * env


def taiko(big=False, rng=np.random.default_rng(21)):
    dur = 2.0 if big else 1.1
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = (45 if big else 62) + 70 * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (2.2 if big else 4.5))
    skin = lp(rng.normal(0, 1, n), 900) * np.exp(-t * 35) * 0.6
    return (body + skin) * (1.0 if big else 0.75)


def string_pad(notes, dur, rng=np.random.default_rng(31)):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in notes:
        f = midi(m)
        for det in (-0.004, 0.0, 0.0045):
            ph = rng.uniform(0, 1)
            out += 2 * ((t * f * (1 + det) + ph) % 1) - 1
    out = lp(out / (len(notes) * 3), 1700, 4)
    att, rel = 0.45, 0.6
    env = np.clip(t / att, 0, 1) * np.clip((dur - t) / rel, 0, 1)
    return out * env


def low_strings(m, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi(m)
    x = (2 * ((t * f) % 1) - 1) * 0.6 + np.sin(2 * np.pi * f * t)
    env = np.clip(t / 0.3, 0, 1) * np.clip((dur - t) / 0.4, 0, 1)
    return lp(x, 500, 4) * env


# ---------------------------------------------------------------- 楽曲データ（ニ長調・ヨナ抜き寄りのペンタトニック）
# 進行: Bm - G - D - A（感動系の定番 vi-IV-I-V）
CHORDS = [
    dict(root=47, pad=[59, 62, 66], arp=[71, 74, 78, 83, 81, 78, 74, 76]),
    dict(root=43, pad=[59, 62, 67], arp=[67, 71, 74, 79, 78, 74, 71, 74]),
    dict(root=50, pad=[57, 62, 66], arp=[69, 74, 78, 81, 86, 81, 78, 74]),
    dict(root=45, pad=[57, 61, 64], arp=[69, 73, 76, 81, 83, 81, 76, 73]),
]
# 笛のメロディ（4小節フレーズ×2）。(拍位置, MIDI, 長さ[拍])
MELODY = [
    [(0, 78, 2), (2, 76, 1), (3, 74, 1)], [(0, 71, 3.5)], [(0, 69, 2), (2, 74, 2)], [(0, 76, 3.5)],
    [(0, 83, 2), (2, 81, 1), (3, 78, 1)], [(0, 79, 1.5), (1.5, 78, 0.5), (2, 74, 2)], [(0, 78, 2), (2, 81, 2)], [(0, 76, 3.8)],
]
TAIKO_MAIN = [1, 0, 0, 1, 1, 0, 0, 0]       # 8分グリッド（ドン・・ドドン）
TAIKO_PEAK = [1, 0, 1, 1, 1, 0, 1, 1]


def put(buf, x, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m] * gain


def reverb(x, secs=2.4, wet=0.28, rng=np.random.default_rng(41)):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, n) * np.exp(-t * 6.5 / secs)
    ir = lp(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    w = fftconvolve(x, ir)[:len(x)]
    return x * (1 - wet) + w * wet * 1.6


def compose(total, hook_end, sus_start, peak):
    """
    hook_end : 本編（第10位）開始時刻
    sus_start: 「そして第1位は」開始時刻
    peak     : 第1位 開始時刻
    """
    n = int(total * SR) + SR * 3
    koto_b = np.zeros(n)
    flute_b = np.zeros(n)
    pad_b = np.zeros(n)
    low_b = np.zeros(n)
    drum_b = np.zeros(n)

    def section(t):
        if t < hook_end:
            return "hook"
        if t < sus_start:
            return "main"
        if t < peak:
            return "sus"
        return "peak"

    # 小節単位で配置（ため区間・頂点は小節の頭に合わせ直す）
    starts = []
    t = 0.0
    while t < hook_end - 0.01:
        starts.append((t, "hook")); t += BAR
    t = hook_end
    while t < sus_start - 0.01:
        starts.append((t, "main")); t += BAR
    t = peak
    while t < total + BAR:
        starts.append((t, "peak")); t += BAR

    for bi, (t0, sec) in enumerate(starts):
        c = CHORDS[bi % 4]
        nxt = starts[bi + 1][0] if bi + 1 < len(starts) else t0 + BAR
        blen = min(BAR, nxt - t0) if sec != "peak" else BAR
        # ストリングス
        put(pad_b, string_pad(c["pad"] + ([c["pad"][0] + 12] if sec == "peak" else []), blen + 0.5), t0,
            0.55 if sec == "hook" else 0.75 if sec == "main" else 1.0)
        if sec != "hook":
            put(low_b, low_strings(c["root"] - 12, blen + 0.3), t0, 0.5 if sec == "main" else 0.7)
        # 琴の分散和音（8分・本編以降は16分の装飾も）
        arp = c["arp"]
        steps = 8
        for e in range(steps):
            at = t0 + e * BEAT / 2
            if at >= t0 + blen:
                break
            vel = 0.55 + 0.25 * (e % 2 == 0)
            put(koto_b, koto(arp[e]), at, vel * (0.8 if sec == "hook" else 1.0))
            if sec == "peak" and e % 2 == 1:
                put(koto_b, koto(arp[e] + 12, 1.2), at + BEAT / 4, 0.3)
        # 笛（本編とクライマックスのみ）
        if sec in ("main", "peak"):
            phrase = MELODY[bi % 8]
            for beat_pos, m, ln in phrase:
                at = t0 + beat_pos * BEAT
                if at >= t0 + blen:
                    continue
                d = min(ln * BEAT, t0 + blen - at + 0.3)
                put(flute_b, flute(m + (12 if sec == "peak" and bi % 2 else 0), d), at, 0.5)
        # 和太鼓
        if sec == "hook":
            put(drum_b, taiko(big=True), t0, 0.6 if bi == 0 else 0.0)
            if bi > 0:
                for e, hit in enumerate(TAIKO_MAIN):
                    if hit and e in (0, 4):
                        put(drum_b, taiko(), t0 + e * BEAT / 2, 0.45)
        else:
            pat = TAIKO_MAIN if sec == "main" else TAIKO_PEAK
            for e, hit in enumerate(pat):
                if hit and t0 + e * BEAT / 2 < t0 + blen:
                    put(drum_b, taiko(), t0 + e * BEAT / 2, (0.75 if e in (0, 4) else 0.5))
            if bi % 4 == 0:
                put(drum_b, taiko(big=True), t0, 0.45 if sec == "main" else 0.7)

    # ため区間: ストリングスの持続音がクレッシェンドし、太鼓が少しずつ近づく
    sd = peak - sus_start
    if sd > 0.2:
        sw = string_pad([50, 57, 62, 66, 69], sd + 0.6)
        sw *= np.linspace(0.3, 1.2, len(sw))
        put(pad_b, sw, sus_start, 1.0)
        put(low_b, low_strings(38, sd + 0.4), sus_start, 0.7)
        k = 0
        tt = sus_start + 0.2
        while tt < peak - 0.25:
            put(drum_b, taiko(), tt, 0.15 + 0.35 * (tt - sus_start) / sd)
            tt += max(0.18, BEAT * (0.9 - 0.15 * k)); k += 1
    put(drum_b, taiko(big=True), peak, 0.9)  # 第1位の幕開け

    pad_b = sosfilt(butter(2, 150, "high", fs=SR, output="sos"), pad_b)  # こもり防止
    music = koto_b * 0.34 + flute_b * 0.36 + pad_b * 0.24 + low_b * 0.14
    music = reverb(music)
    drums = reverb(drum_b, secs=1.6, wet=0.18) * 0.55
    out = music + drums
    out = sosfilt(butter(2, 35, "high", fs=SR, output="sos"), out)  # 超低域カット
    # 冒頭のフェードイン
    fi = int(0.08 * SR)
    out[:fi] *= np.linspace(0, 1, fi)
    out = out[:int(total * SR)]
    return out / (np.max(np.abs(out)) + 1e-9) * 0.9
