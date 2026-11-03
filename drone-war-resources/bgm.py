# -*- coding: utf-8 -*-
"""テック系ドキュメンタリー風BGMをプログラムで合成する(外部音源不要・権利フリー)。
Eマイナー / 84BPM。低音の脈動ベース + 倍音パッド + 柔らかいキック + まばらなプラック + 簡易リバーブ。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 84
BEAT = 60.0 / BPM
BAR = BEAT * 4

# コード進行(MIDIノート)。8小節でループ
PROG = [
    [52, 55, 59, 64],  # Em
    [48, 52, 55, 59],  # Cmaj7
    [55, 59, 62, 66],  # G
    [50, 54, 57, 62],  # D
    [52, 55, 59, 64],  # Em
    [48, 52, 55, 59],  # C
    [45, 48, 52, 57],  # Am
    [47, 50, 54, 59],  # Bm
]
ROOTS = [52, 48, 55, 50, 52, 48, 45, 47]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s]

def env_ar(n, a, r):
    env = np.ones(n, dtype=np.float32)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    env[:na] = np.linspace(0, 1, na); env[n - nr:] = np.linspace(1, 0, nr)
    return env

def pad_note(f, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.0015 * np.sin(2 * np.pi * 0.19 * t + rng.uniform(0, 6.28))
    sig = np.zeros(n, dtype=np.float32)
    for det in (-0.003, 0.003):
        for h in range(1, 6):
            sig += (1 / h ** 1.9) * np.sin(2 * np.pi * f * h * (1 + det) * vib * t + rng.uniform(0, 6.28))
    return sig

def bass_pulse(f, dur=0.33):
    """サブベースの短い脈動(サイン + 弱い2倍音、速いディケイ)"""
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 0.14)).astype(np.float32)

def kick(rng, dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 42 + 70 * np.exp(-t / 0.045)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    click = rng.standard_normal(n).astype(np.float32) * np.exp(-t / 0.006)
    click = np.convolve(click, np.ones(64) / 64, mode='same')
    return (body + 0.15 * click).astype(np.float32)

def tick(rng, dur=0.08):
    """柔らかいハイハット風のノイズ"""
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32) * np.exp(-t / 0.018)
    return (x - np.convolve(x, np.ones(24) / 24, mode='same')).astype(np.float32)  # 低域を抜く

def pluck(f, dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t))
            * np.exp(-t / 0.3)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y))
        y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.3):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.72), (1877, 0.70), (2251, 0.68), (12007, 0.45))) / 4
    return (1 - mix) * x + mix * wet

def generate(total, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    pad = np.zeros(n, dtype=np.float32); bass = np.zeros(n, dtype=np.float32)
    drums = np.zeros(n, dtype=np.float32); arp = np.zeros(n, dtype=np.float32)
    nbars = int(np.ceil(total / BAR))
    for b in range(nbars):
        t0 = b * BAR; chord = PROG[b % 8]
        dur = BAR + 1.0
        sig = sum(pad_note(midi(m), dur, rng) * (0.9 if i < 3 else 0.5) for i, m in enumerate(chord))
        add(pad, t0, sig * env_ar(len(sig), 0.8, 1.0))
        # ベース: 8分音符の脈動(ルートの2オクターブ下、たまに5度)
        inten = min(1.0, max(0.0, (t0 - 6) / 14))
        root = ROOTS[b % 8] - 24
        for k in range(8):
            note = root if k % 4 != 3 else root + 7
            vel = (1.0 if k % 2 == 0 else 0.55) * inten
            add(bass, t0 + k * BEAT / 2, bass_pulse(midi(note)) * vel)
        # ドラム: キック 1・3 拍、ティック 8 分裏(20 秒以降)
        if inten > 0:
            add(drums, t0, kick(rng) * inten)
            add(drums, t0 + 2 * BEAT, kick(rng) * 0.8 * inten)
            if t0 > 20:
                for k in range(8):
                    add(drums, t0 + k * BEAT / 2 + BEAT / 4, tick(rng) * 0.12 * (1.0 if k % 2 else 0.6))
        # プラック: 16 秒以降、まばら
        if t0 > 16:
            for k in range(8):
                if rng.random() < 0.4:
                    m = chord[rng.integers(0, 4)] + 24
                    add(arp, t0 + k * BEAT / 2, pluck(midi(m)) * rng.uniform(0.4, 1.0))
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.5 * norm(pad) + 0.55 * norm(bass) + 0.6 * norm(drums) + 0.16 * reverb(norm(arp), 0.5)
    mix = reverb(mix, 0.15)
    mix *= env_ar(len(mix), 2.0, 5.0)
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
