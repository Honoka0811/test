"""自作BGM: ノワール風のスウィング・ジャズ(ウォーキングベース+エレピ+ブラシ)。素材は一切使わず数値合成。"""
import json
import pathlib
import wave

import numpy as np

SR = 48000
OUT = pathlib.Path(__file__).parent / "output"
BPM = 104
BEAT = 60 / BPM
rng = np.random.default_rng(7)


def hz(n):  # MIDIノート -> 周波数
    return 440 * 2 ** ((n - 69) / 12)


def add(buf, start, sig, pan=0.5, gain=1.0):
    i = int(start * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig), 0] += sig * gain * np.cos(pan * np.pi / 2)
    buf[i:i + len(sig), 1] += sig * gain * np.sin(pan * np.pi / 2)


def bass(note, dur):
    t = np.arange(int(dur * SR)) / SR
    f = hz(note)
    s = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(4 * np.pi * f * t) * np.exp(-t * 6) \
        + 0.2 * np.sin(6 * np.pi * f * t) * np.exp(-t * 10)
    env = np.minimum(t / 0.008, 1) * np.exp(-t * 2.2) * np.minimum((dur - t) / 0.03, 1)
    return s * env


def epiano(note, dur):
    t = np.arange(int(dur * SR)) / SR
    f = hz(note)
    mod = np.sin(2 * np.pi * f * 14 * t) * 0.35 * np.exp(-t * 18) + np.sin(2 * np.pi * f * t) * 1.1 * np.exp(-t * 2.5)
    s = np.sin(2 * np.pi * f * t + mod) * (1 + 0.12 * np.sin(2 * np.pi * 4.6 * t))
    env = np.minimum(t / 0.004, 1) * np.exp(-t * 1.6) * np.minimum((dur - t) / 0.08, 1)
    return s * env


def brush(dur, bright=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0) * bright + noise * (1 - bright) * 0.3
    return noise * np.minimum(t / 0.002, 1) * np.exp(-t * (28 if dur < 0.2 else 9))


def snap():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    s = rng.standard_normal(n) * np.exp(-t * 70) + np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 90) * 0.6
    return s


# Dm9 | Bbmaj7 | Gm9 | A7(b9)  — 1小節ずつ
CHORDS = [
    ([62, 65, 69, 72, 76], [38, 41, 45, 44]),
    ([58, 62, 65, 69, 72], [34, 38, 41, 40]),
    ([55, 58, 62, 65, 69], [31, 34, 38, 39]),
    ([57, 61, 64, 67, 70], [33, 37, 40, 37]),
]


def main():
    total = json.loads((OUT / "timeline.json").read_text())["duration"]
    buf = np.zeros((int((total + 1) * SR), 2), np.float32)
    bar, t0 = 0, 0.0
    swing = BEAT * 2 / 3
    while t0 < total - 3.5:
        notes, walk = CHORDS[bar % 4]
        for b in range(4):
            tb = t0 + b * BEAT
            add(buf, tb, bass(walk[b], BEAT * 0.95), 0.5, 0.5)
            add(buf, tb, brush(0.35, 0.6), 0.7, 0.05)                 # ライド
            if b in (1, 3):
                add(buf, tb + swing, brush(0.12, 0.8), 0.7, 0.04)     # スウィングの裏
                add(buf, tb, snap(), 0.3, 0.10)                       # 2・4拍のスナップ
        # エレピ: 1拍目と2拍裏にコンピング
        for off, vel, length in ((0, 0.085, BEAT * 1.6), (BEAT + swing, 0.06, BEAT * 2)):
            for k, n in enumerate(notes):
                add(buf, t0 + off + k * 0.012, epiano(n, length), 0.3 + 0.1 * k, vel)
        # 2小節に1回、高音の合いの手
        if bar % 2 == 1:
            for k, n in enumerate((notes[-1] + 12, notes[-2] + 12, notes[-3] + 12)):
                add(buf, t0 + 2 * BEAT + k * swing, epiano(n, BEAT), 0.6, 0.05)
        bar += 1
        t0 += 4 * BEAT
    # エンディング: Dm(maj9) を鳴らして余韻
    for k, n in enumerate([50, 57, 62, 65, 69, 73, 76]):
        add(buf, t0 + k * 0.05, epiano(n, 3.4), 0.3 + 0.06 * k, 0.09)
    add(buf, t0, bass(38, 3.2), 0.5, 0.55)
    # 簡易リバーブ(複数ディレイ)
    wet = np.zeros_like(buf)
    for d, g in ((0.031, 0.35), (0.047, 0.28), (0.083, 0.2), (0.127, 0.14), (0.211, 0.09)):
        k = int(d * SR)
        wet[k:] += buf[:-k][:, ::-1] * g
    buf += wet * 0.5
    fade = int(0.6 * SR)
    buf[:fade] *= np.linspace(0, 1, fade)[:, None]
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    buf = buf[: int(total * SR)]
    buf[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
    buf *= 0.8 / np.abs(buf).max()
    with wave.open(str(OUT / "bgm.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    print("bgm", total, "sec, bars", bar)


if __name__ == "__main__":
    main()
