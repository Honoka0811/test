"""動画用のオリジナルBGMを合成する（外部素材不使用・numpyのみ）。

ニュース解説向けの落ち着いた電子音: 100 BPM、Aマイナー、Am–F–C–G のループ。
パッド + ベースのパルス + 16分アルペジオ + 控えめなハイハットとキック。
  python bgm.py <秒数> <出力wav>
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 100
BEAT = 60 / BPM
BAR = BEAT * 4

A = 110.0  # A2


def note(semi: float, base: float = A) -> float:
    return base * 2 ** (semi / 12)


# コード進行（ルートからの半音: 構成音）。Am, F, C, G
CHORDS = [
    (0, [0, 3, 7, 12]),       # Am
    (-4, [0, 4, 7, 12]),      # F
    (3, [0, 4, 7, 12]),       # C
    (-2, [0, 4, 7, 12]),      # G
]


def env(n: int, attack: float, release: float, hold: float = 0.0) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    total = n / SR
    r = np.clip((total - t) / max(release, 1e-4), 0, 1)
    return a * r


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    # 1次IIRを2回かけた簡易ローパス
    rc = 1 / (2 * np.pi * cutoff)
    alpha = (1 / SR) / (rc + 1 / SR)
    y = np.empty_like(x)
    acc = 0.0
    for _ in range(2):
        acc = 0.0
        for i in range(len(x)):
            acc += alpha * (x[i] - acc)
            y[i] = acc
        x = y.copy()
    return y


def pad(chord_root: float, intervals, n: int, t0: float) -> np.ndarray:
    t = np.arange(n) / SR + t0
    out = np.zeros(n)
    for iv in intervals:
        f = note(chord_root + iv, A * 2)
        for det in (-0.4, 0.0, 0.4):
            fd = f * 2 ** (det / 1200 * 8)
            out += np.sin(2 * np.pi * fd * t + 0.3 * np.sin(2 * np.pi * 0.2 * t))
    out /= len(intervals) * 3
    return out * env(n, 0.6, 0.8)


def pluck(f: float, n: int) -> np.ndarray:
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return tone * np.exp(-t * 9) * env(n, 0.003, 0.02)


def bass(f: float, n: int) -> np.ndarray:
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.15 * np.sign(np.sin(2 * np.pi * f * t))
    return tone * np.exp(-t * 4) * env(n, 0.005, 0.05)


def kick(n: int) -> np.ndarray:
    t = np.arange(n) / SR
    f = 55 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * env(n, 0.002, 0.02)


def hat(n: int, rng: np.random.Generator, accent: float) -> np.ndarray:
    x = rng.standard_normal(n)
    x = x - lowpass(x, 5000)  # ざっくりハイパス
    t = np.arange(n) / SR
    return x * np.exp(-t * 70) * 0.5 * accent


def render(duration: float) -> np.ndarray:
    rng = np.random.default_rng(7)
    total = int(duration * SR)
    bars = int(np.ceil(duration / BAR)) + 1
    buf_len = int(bars * BAR * SR) + 2 * SR  # 最終小節がはみ出しても収まる長さ
    L = np.zeros(buf_len)
    R = np.zeros(buf_len)
    for b in range(bars):
        root, ivs = CHORDS[b % len(CHORDS)]
        s = int(b * BAR * SR)
        n = int(BAR * SR)
        # パッド（左右で位相をずらして広がりを出す）
        p = pad(root, ivs, n, b * BAR)
        L[s:s + n] += 0.22 * p
        R[s:s + n] += 0.22 * np.roll(p, 300)
        for beat in range(4):
            bs = s + int(beat * BEAT * SR)
            bn = int(BEAT * SR)
            bb = bass(note(root), bn)
            L[bs:bs + bn] += 0.28 * bb
            R[bs:bs + bn] += 0.28 * bb
            if beat in (0, 2):
                k = kick(bn)
                L[bs:bs + bn] += 0.18 * k
                R[bs:bs + bn] += 0.18 * k
            for e in range(2):  # 8分ハイハット
                hs = bs + int(e * BEAT / 2 * SR)
                hn = int(BEAT / 2 * SR)
                h = hat(hn, rng, 0.35 if e == 0 else 0.6)
                L[hs:hs + hn] += 0.05 * h
                R[hs:hs + hn] += 0.05 * np.roll(h, 40)
            for q in range(4):  # 16分アルペジオ
                qs = bs + int(q * BEAT / 4 * SR)
                qn = int(BEAT / 4 * SR)
                iv = ivs[(beat * 4 + q) % len(ivs)]
                pl = pluck(note(root + iv, A * 4), qn)
                pan = 0.5 + 0.4 * np.sin((beat * 4 + q) * 0.9)
                L[qs:qs + qn] += 0.10 * pl * (1 - pan)
                R[qs:qs + qn] += 0.10 * pl * pan
    stereo = np.stack([L[:total], R[:total]], axis=1)
    # 全体のフェードイン/アウト
    fade = np.ones(total)
    fi, fo = int(1.0 * SR), int(2.5 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    stereo *= fade[:, None]
    stereo = np.tanh(stereo * 1.4) * 0.8
    return stereo


def main() -> None:
    duration = float(sys.argv[1])
    out = sys.argv[2]
    audio = render(duration)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("bgm:", out, f"{duration:.1f}s")


if __name__ == "__main__":
    main()
