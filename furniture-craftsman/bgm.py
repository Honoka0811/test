# -*- coding: utf-8 -*-
"""ほのぼの系BGMを numpy だけで合成する(外部音源不要・権利フリー)。
Cメジャー / 100BPM。マリンバ風メロディ + ナイロン弦風アルペジオ + やわらかいベース + ウッドブロック + シェイカー。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 100
BEAT = 60.0 / BPM
BAR = BEAT * 4

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

# 8小節ループ: C – G/B – Am – F – C – G – F – G
CHORDS = [
    (48, [60, 64, 67, 72]),   # C
    (47, [59, 62, 67, 71]),   # G/B
    (45, [57, 60, 64, 69]),   # Am
    (41, [57, 60, 65, 69]),   # F
    (48, [60, 64, 67, 72]),   # C
    (43, [59, 62, 67, 71]),   # G
    (41, [57, 60, 65, 69]),   # F
    (43, [59, 62, 65, 67]),   # G7
]
# メロディ(小節ごとに (拍位置, MIDIノート, 拍数))。A/B の 16 小節で一巡
MELODY = [
    [(0, 76, 1), (1, 79, 1), (2, 84, 1.5), (3.5, 83, .5)],
    [(0, 79, 2), (2.5, 74, .5), (3, 79, 1)],
    [(0, 76, 1), (1, 72, 1), (2, 76, 1.5), (3.5, 74, .5)],
    [(0, 72, 3)],
    [(0, 76, 1), (1, 79, 1), (2, 84, 1), (3, 88, 1)],
    [(0, 86, 1.5), (1.5, 83, .5), (2, 79, 2)],
    [(0, 81, 1), (1, 84, 1), (2, 81, 1), (3, 77, 1)],
    [(0, 79, 2), (2, 74, 1), (3, 79, 1)],
    [(0.5, 79, .5), (1, 76, 1), (2.5, 79, .5), (3, 76, 1)],
    [(0, 74, 1.5), (1.5, 71, .5), (2, 67, 2)],
    [(0.5, 76, .5), (1, 72, 1), (2.5, 76, .5), (3, 72, 1)],
    [(0, 69, 1), (1, 72, 1), (2, 77, 2)],
    [(0, 76, 1), (1, 79, 1), (2, 84, 1.5), (3.5, 83, .5)],
    [(0, 79, 1), (1, 83, 1), (2, 86, 2)],
    [(0, 84, 1), (1, 81, 1), (2, 77, 1), (3, 81, 1)],
    [(0, 79, 1), (1, 77, 1), (2, 74, 1), (3, 71, 1)],
]

def add(buf, start_s, sig, pan=0.5):
    """ステレオバッファに定位つきで加算"""
    s = int(start_s * SR)
    if s >= len(buf): return
    e = min(s + len(sig), len(buf))
    buf[s:e, 0] += sig[:e - s] * np.cos(pan * np.pi / 2)
    buf[s:e, 1] += sig[:e - s] * np.sin(pan * np.pi / 2)

def marimba(f, dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.38)
           + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.09)
           + 0.10 * np.sin(2 * np.pi * 10 * f * t) * np.exp(-t / 0.025))
    sig[:96] *= np.linspace(0, 1, 96)
    return sig.astype(np.float32)

def guitar(f, dur=1.8):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n)
    for h in range(1, 9):
        sig += (1 / h ** 1.3) * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (1.6 + 0.9 * h))
    sig[:144] *= np.linspace(0, 1, 144)
    return sig.astype(np.float32)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.9)
    a = int(0.012 * SR); r = int(0.06 * SR)
    sig[:a] *= np.linspace(0, 1, a); sig[-r:] *= np.linspace(1, 0, r)
    return sig.astype(np.float32)

def woodblock(f=880.0):
    n = int(0.12 * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.7 * t)) * np.exp(-t / 0.018)
    sig[:48] *= np.linspace(0, 1, 48)
    return sig.astype(np.float32)

def shaker(rng, dur=0.07):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = np.diff(x, prepend=0.0)             # 簡易ハイパス
    return (x * np.exp(-t / 0.02)).astype(np.float32)

def reverb(buf, rng):
    """短いコムフィルタ数本による簡易リバーブ"""
    wet = np.zeros_like(buf)
    for d, g in ((0.031, .32), (0.047, .27), (0.071, .22), (0.113, .17), (0.167, .12)):
        k = int(d * SR)
        wet[k:, 0] += buf[:-k, 1] * g
        wet[k:, 1] += buf[:-k, 0] * g
    return buf + 0.55 * wet

def generate(total):
    """total 秒のステレオBGM (N,2) float32 を返す"""
    rng = np.random.default_rng(7)
    n = int(total * SR) + 1
    buf = np.zeros((n, 2), dtype=np.float32)
    bars = int(np.ceil(total / BAR)) + 1
    arp = [0, 2, 1, 2, 3, 2, 1, 2]                       # 8分音符のアルペジオ型
    for b in range(bars):
        t0 = b * BAR
        root, chord = CHORDS[b % 8]
        intro = b < 2                                      # 冒頭2小節はアルペジオだけ
        add(buf, t0, bass(midi(root - 12), BEAT * 2.4) * 0.50)
        add(buf, t0 + BEAT * 2.5, bass(midi(root - 12), BEAT * 1.3) * 0.36)
        for i, k in enumerate(arp):
            v = 0.20 * (1.0 if i % 2 == 0 else 0.72) * rng.uniform(0.9, 1.05)
            add(buf, t0 + i * BEAT / 2 + rng.uniform(0, 0.006), guitar(midi(chord[k])) * v, pan=0.32)
        if not intro:
            for beat, note, _len in MELODY[(b - 2) % 16]:
                add(buf, t0 + beat * BEAT, marimba(midi(note)) * 0.26 * rng.uniform(0.88, 1.0), pan=0.64)
            for beat in (1, 3):
                add(buf, t0 + beat * BEAT, woodblock(880 if beat == 1 else 660) * 0.10, pan=0.75)
            for i in range(8):
                add(buf, t0 + i * BEAT / 2, shaker(rng) * (0.035 if i % 2 else 0.018), pan=0.25)
    buf = reverb(buf, rng)
    # 終わりは最後のコードを C に解決させてフェードアウト
    end = marimba(midi(72), 2.5) * 0.3 + marimba(midi(76), 2.5) * 0.22 + guitar(midi(48), 2.5) * 0.3
    fade = int(2.2 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    add(buf, max(0, total - 2.4), end * np.linspace(1, 0, len(end)), pan=0.5)
    fi = int(0.4 * SR); buf[:fi] *= np.linspace(0, 1, fi)[:, None]
    buf = buf / np.max(np.abs(buf)) * 0.9
    return buf[:n].astype(np.float32)

if __name__ == '__main__':
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 57.5
    out = sys.argv[2] if len(sys.argv) > 2 else 'output/bgm.wav'
    x = generate(dur)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{dur:.1f}s')
