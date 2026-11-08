# -*- coding: utf-8 -*-
"""サスペンスBGM(自作・権利フリー)を numpy だけで合成する。
視聴者を引きつける要素:
  - 心拍(60BPM の「ドクン」)… 生理的な緊張感。映像の明滅と同期
  - 時計の秒針(チッ、チッ)… 「3分間」のモチーフ。時間に追われる感覚
  - 低音ドローン(D + 不協和な Eb)… 不穏な土台
  - 暗いパッド(Dマイナー add9)… 8秒周期でうねる
  - シーン転換のライザー+ブーム … 場面が変わる瞬間に耳を引く
使い方: python3 bgm.py [長さ秒] [出力wav]  /  import bgm; bgm.generate(58)
"""
import sys
import numpy as np

SR = 48000

def _env(n, a, r):
    """アタック a 秒・リリース r 秒の簡易エンベロープ"""
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
    """60BPM の lub-dub"""
    tr = np.zeros(int(total * SR), dtype=np.float32)
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    f = 58 * np.exp(-t * 9) + 34                      # 58→34Hz スイープ
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)
    thump *= np.exp(-t * 16).astype(np.float32)
    for b in range(int(total)):
        _place(tr, thump * 0.9, b)            # ドッ
        _place(tr, thump * 0.55, b + 0.22)    # クン
    return tr

def _tick(total, rng):
    """秒針。tick/tock で高さを交互に"""
    tr = np.zeros(int(total * SR), dtype=np.float32)
    n = int(0.028 * SR)
    t = np.arange(n) / SR
    for b in range(int(total)):
        f0 = 2300 if b % 2 == 0 else 1800
        click = (np.sin(2 * np.pi * f0 * t) * 0.6 +
                 rng.standard_normal(n) * 0.5).astype(np.float32)
        click *= np.exp(-t * 260).astype(np.float32)
        _place(tr, click * 0.5, b + 0.5)
    return tr

def _drone(total):
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    # D1/D2 + かすかな Eb(短2度の不協和)
    for f, g in [(36.71, 0.55), (73.42, 0.4), (77.78, 0.07), (110.0, 0.1)]:
        ph = 2 * np.pi * f * t
        out += (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)).astype(np.float32) * g
    lfo = (0.75 + 0.25 * np.sin(2 * np.pi * t / 13.0)).astype(np.float32)
    return out * lfo * 0.5

def _pad(total):
    """Dマイナー add9 のうねるパッド(8秒周期)"""
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    for f, g in [(146.83, 0.30), (174.61, 0.26), (220.0, 0.22), (329.63, 0.10)]:
        for det in (-1.5, 1.5):
            out += np.sin(2 * np.pi * (f + det * 0.7) * t + f).astype(np.float32) * g * 0.5
    swell = (0.35 + 0.65 * (0.5 - 0.5 * np.cos(2 * np.pi * t / 8.0)) ** 1.6).astype(np.float32)
    return out * swell * 0.33

def _arp(total, rng):
    """まばらな不穏アルペジオ(D, F, E, Bb)+エコー"""
    tr = np.zeros(int(total * SR), dtype=np.float32)
    notes = [293.66, 349.23, 329.63, 233.08, 293.66, 440.0]
    k = 0
    beat = 0.0
    while beat < total - 2:
        if rng.random() < 0.6:
            f = notes[k % len(notes)]; k += 1
            dur = 0.9
            n = int(dur * SR)
            t = np.arange(n) / SR
            x = (np.sin(2 * np.pi * f * t) * 0.6 +
                 np.sin(2 * np.pi * f * 2.004 * t) * 0.18).astype(np.float32)
            x *= (np.exp(-t * 4.2) * _env(n, 0.004, 0.05)).astype(np.float32)
            _place(tr, x * 0.30, beat)
            _place(tr, x * 0.14, beat + 0.375)   # エコー
            _place(tr, x * 0.07, beat + 0.75)
        beat += 2.0
    return tr

def _riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    g = (t / dur) ** 2.6
    noise = np.random.default_rng(7).standard_normal(n).astype(np.float32)
    # 簡易ハイパス(差分)
    noise = np.diff(noise, prepend=0.0).astype(np.float32)
    tone = np.sin(2 * np.pi * np.cumsum(180 + 520 * (t / dur) ** 2) / SR).astype(np.float32)
    return (noise * 0.5 + tone * 0.35) * g.astype(np.float32)

def _boom():
    n = int(1.3 * SR)
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 10) + 32
    x = np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)
    x *= np.exp(-t * 3.2).astype(np.float32)
    return x

def _reverb(x):
    out = x.copy()
    for d, g in [(0.091, 0.28), (0.137, 0.22), (0.211, 0.16), (0.293, 0.11)]:
        nd = int(d * SR)
        out[nd:] += x[:-nd] * g
    return out

def generate(total):
    """total 秒のサスペンスBGM(モノラル float32 / 48kHz)を返す"""
    rng = np.random.default_rng(1968)
    n = int(total * SR)
    mix = np.zeros(n, dtype=np.float32)

    mix += _drone(total)
    mix += _pad(total)
    mix += _heartbeat(total) * 0.8
    mix += _tick(total, rng) * 0.7
    mix += _arp(total, rng)

    # シーン転換(render.html の SCENES と対応): 6/15/22/31/39/48.5 秒
    for cut in [6, 15, 22, 31, 39, 48.5]:
        if cut < total:
            r = _riser(2.2)
            _place(mix, r * 0.5, max(0, cut - 2.2))
            _place(mix, _boom() * 0.55, cut)
    # 冒頭のインパクトとスタンプ(3.4s)・時効スタンプ(45.4s)
    _place(mix, _boom() * 0.7, 0.05)
    _place(mix, _boom() * 0.5, 3.45)
    if total > 45.5: _place(mix, _boom() * 0.5, 45.4)

    mix = _reverb(mix)
    # エンディングへ向けてフェードアウト(最後 1.2 秒)
    nf = int(1.2 * SR)
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
