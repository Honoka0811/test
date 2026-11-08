# -*- coding: utf-8 -*-
"""ホラーBGM(自作・権利フリー)を numpy だけで合成する。不気味系フォーマット用。
構成要素:
  - 狂ったオルゴール … わずかに音程のずれた2声のベル。childlike × 不協和で不気味さの核
  - 遅い心拍(45BPM)… ep001より遅く、重く
  - 低音ドローン(A + 三全音 Eb)… 「悪魔の音程」で土台から不安に
  - 風 … バンドパスしたノイズのうなり
  - 軋み音 … 床板が軋むような短い低音ベンドを不定期に
  - シーン転換のライザー+ブーム(7/14/23/31/40/48.5秒)
使い方: python3 bgm.py [長さ秒] [出力wav]  /  import bgm; bgm.generate(58)
"""
import sys
import numpy as np

SR = 48000

def _env(n, a, r):
    e = np.ones(n, dtype=np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na > 0: e[:na] = np.linspace(0, 1, na)
    if nr > 0: e[-nr:] *= np.linspace(1, 0, nr)
    return e

def _place(track, x, at):
    s = int(at * SR)
    if s >= len(track): return
    e = min(s + len(x), len(track))
    track[s:e] += x[:e - s]

def _heartbeat(total):
    """45BPM の重い lub-dub"""
    tr = np.zeros(int(total * SR), dtype=np.float32)
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    f = 52 * np.exp(-t * 8) + 30
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)
    thump *= np.exp(-t * 13).astype(np.float32)
    period = 60 / 45.0
    b = 0.0
    while b < total:
        _place(tr, thump * 0.9, b)
        _place(tr, thump * 0.5, b + 0.28)
        b += period
    return tr

def _musicbox(total, rng):
    """狂ったオルゴール: Aマイナーの単旋律、2声が +10セントずれて重なる"""
    tr = np.zeros(int(total * SR), dtype=np.float32)
    # A4, C5, E5, B4, G#4 … 不穏に半音を混ぜた旋律
    melody = [440.0, 523.25, 440.0, 659.26, 523.25, 415.30, 440.0, 493.88]
    k = 0
    beat = 1.0
    while beat < total - 3:
        if rng.random() < 0.72:
            f = melody[k % len(melody)]; k += 1
            n = int(2.4 * SR)
            t = np.arange(n) / SR
            x = np.zeros(n, dtype=np.float32)
            for det, g in [(1.0, 0.55), (1.0058, 0.45)]:        # +10セントのゆがみ
                for h, hg in [(1, 1.0), (4.2, 0.18), (7.9, 0.07)]:  # ベル風の非整数倍音
                    x += np.sin(2 * np.pi * f * det * h * t).astype(np.float32) * g * hg
            x *= (np.exp(-t * 2.6) * _env(n, 0.002, 0.1)).astype(np.float32)
            _place(tr, x * 0.16, beat)
        beat += 1.6
    return tr

def _drone(total):
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    # A1 + E2 + 三全音 Eb2(55 / 82.4 / 77.78Hz)
    for f, g in [(55.0, 0.55), (82.41, 0.22), (77.78, 0.16), (110.0, 0.12)]:
        ph = 2 * np.pi * f * t
        out += (np.sin(ph) + 0.3 * np.sin(2 * ph + 0.7)).astype(np.float32) * g
    lfo = (0.7 + 0.3 * np.sin(2 * np.pi * t / 17.0 + 1.1)).astype(np.float32)
    return out * lfo * 0.5

def _wind(total, rng):
    n = int(total * SR)
    x = rng.standard_normal(n).astype(np.float32)
    # FFTで中低域だけ残すバンドパス(風のうなり)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    band = np.exp(-((freqs - 300) / 220.0) ** 2) + 0.4 * np.exp(-((freqs - 90) / 60.0) ** 2)
    x = np.fft.irfft(X * band, n).astype(np.float32)
    t = np.arange(n) / SR
    gust = (0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 11.0 + np.sin(t * 0.23) * 2)) ** 2).astype(np.float32)
    x /= max(1e-6, np.max(np.abs(x)))
    return x * gust * 0.5

def _creaks(total, rng):
    """床板の軋み: 短い低音のピッチベンド"""
    tr = np.zeros(int(total * SR), dtype=np.float32)
    at = 2.5
    while at < total - 1:
        if rng.random() < 0.5:
            n = int(0.5 * SR)
            t = np.arange(n) / SR
            f0 = 90 + rng.random() * 60
            f = f0 * (1 + 0.5 * np.sin(2 * np.pi * t / 0.5 * 0.5))
            x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)).astype(np.float32)   # 矩形波=木の軋み感
            # 丸める
            X = np.fft.rfft(x)
            fr = np.fft.rfftfreq(n, 1 / SR)
            x = np.fft.irfft(X * np.exp(-fr / 900.0), n).astype(np.float32)
            x *= _env(n, 0.06, 0.3) * np.float32(0.11)
            _place(tr, x, at)
        at += 3.0 + rng.random() * 4.0
    return tr

def _riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    g = (t / dur) ** 2.8
    noise = np.random.default_rng(13).standard_normal(n).astype(np.float32)
    noise = np.diff(noise, prepend=0.0).astype(np.float32)
    tone = np.sin(2 * np.pi * np.cumsum(110 + 420 * (t / dur) ** 2) / SR).astype(np.float32)
    return (noise * 0.45 + tone * 0.3) * g.astype(np.float32)

def _boom():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    f = 100 * np.exp(-t * 9) + 28
    x = np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)
    x *= np.exp(-t * 2.6).astype(np.float32)
    return x

def _reverb(x):
    out = x.copy()
    for d, g in [(0.113, 0.3), (0.167, 0.24), (0.251, 0.17), (0.367, 0.12)]:
        nd = int(d * SR)
        out[nd:] += x[:-nd] * g
    return out

def generate(total):
    """total 秒のホラーBGM(モノラル float32 / 48kHz)を返す"""
    rng = np.random.default_rng(1922)
    n = int(total * SR)
    mix = np.zeros(n, dtype=np.float32)

    mix += _drone(total)
    mix += _wind(total, rng)
    mix += _heartbeat(total) * 0.7
    mix += _musicbox(total, rng)
    mix += _creaks(total, rng)

    # シーン転換(render.html の SCENES と対応)
    for cut in [7, 14, 23, 31, 40, 48.5]:
        if cut < total:
            _place(mix, _riser(2.4) * 0.45, max(0, cut - 2.4))
            _place(mix, _boom() * (0.6 if cut == 31 else 0.45), cut)
    _place(mix, _boom() * 0.5, 0.05)          # 冒頭
    _place(mix, _boom() * 0.4, 4.0)           # 「出た足跡が、ない」
    if total > 46.9: _place(mix, _boom() * 0.45, 46.9)   # 未解決のまま スタンプ

    mix = _reverb(mix)
    nf = int(1.5 * SR)
    mix[-nf:] *= np.linspace(1, 0, nf).astype(np.float32)
    mix /= max(1.0, np.max(np.abs(mix)) / 0.9)
    return mix.astype(np.float32)

if __name__ == '__main__':
    import wave
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 58.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'output/bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{total}s')
