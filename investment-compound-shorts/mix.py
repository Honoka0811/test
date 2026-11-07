# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング) + 効果音をミックスし、無音動画に合成する。
使い方: python3 mix.py [入力mp4=output/video_silent.mp4] [出力mp4=output/compound_shorts.mp4]
効果音はすべて numpy で合成(権利フリー)。キュー時刻は render.html の演出タイミングと対応。
"""
import os, sys, wave, subprocess
import numpy as np
from scipy.signal import butter, sosfilt
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'compound_shorts.mp4')
SR = 48000
TOTAL = 57.5

def read_wav(p):
    with wave.open(p) as w:
        assert w.getframerate() == SR
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
def write_wav(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
def lp(x, fc): return sosfilt(butter(2, fc / (SR / 2), 'low', output='sos'), x)
def hp(x, fc): return sosfilt(butter(2, fc / (SR / 2), 'high', output='sos'), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos'), x)
def add(buf, t, sig, g=1.0):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * g

rng = np.random.default_rng(3)
# ---------- 効果音 ----------
def whoosh(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR; p = t / dur
    x = np.zeros(n)
    noise = rng.standard_normal(n)
    for i in range(6):
        a, b = int(n * i / 6), int(n * (i + 1) / 6)
        fc = 400 + 3000 * np.sin(np.pi * (i + 0.5) / 6)
        x[a:b] = bp(noise, fc * 0.7, fc * 1.5)[a:b]
    return (x * np.sin(np.pi * p) ** 1.5 * 0.8).astype(np.float32)
def slam(dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.25)
    noise = lp(rng.standard_normal(n), 3000) * np.exp(-t / 0.08)
    return np.tanh(1.6 * (sub + 0.7 * noise)).astype(np.float32)
def pop(f=900, dur=0.18):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-t / 0.01))) / SR) * np.exp(-t / 0.05)
    return (x * 0.8).astype(np.float32)
def coin(f=2200, dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 1.5 * t)) * np.exp(-t / 0.09)
    x[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    x += (np.sin(2 * np.pi * f * 1.31 * t)) * np.exp(-t / 0.04) * 0.5  # 2 枚目が当たる感じ
    return (x * 0.6).astype(np.float32)
def ding(f=1320, dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t / (0.5 / k)) / k for k in (1, 2, 3, 4.2))
    return (x * 0.5).astype(np.float32)
def sparkle(dur=1.0):
    n = int(dur * SR); x = np.zeros(n, np.float32)
    for i in range(10):
        add(x, i * 0.07, coin(1800 * 2 ** (i / 12 * 1.2), 0.3), 0.5)
    return x
def tick(dur=0.03):
    n = int(dur * SR); t = np.arange(n) / SR
    return (hp(rng.standard_normal(n), 3000) * np.exp(-t / 0.006)).astype(np.float32)
def sting(dur=1.2):
    """ハテナの溜め: 低いうなり + 不穏な上昇音"""
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (t / dur * 0.5)) / SR) * np.exp(-t / 0.6)
    x += 0.5 * np.sin(2 * np.pi * np.cumsum(165 * 2 ** (t / dur * 0.5)) / SR) * np.exp(-t / 0.6)
    return (x * 0.5).astype(np.float32)

sfx = np.zeros(int(TOTAL * SR), np.float32)
SLAMS = [0.05, 12.55, 27.0, 33.3, 37.3, 42.9, 47.9, 52.0]
for t in SLAMS: add(sfx, t, slam(), 1.0 if t in (0.05, 12.55, 37.3) else 0.7)
for t in (0.95, 5.0, 11.5, 18.5, 30.0, 30.2, 33.5, 39.5, 50.0): add(sfx, t, whoosh(), 0.8)
for t in (0.95, 8.25, 13.5, 21.5, 24.05, 26.6, 40.9, 44.45, 46.2, 54.0): add(sfx, t, pop(), 0.7)
for t in (7.0, 12.6, 26.6, 42.95, 54.05): add(sfx, t, ding(), 0.7)
add(sfx, 12.5, sparkle(), 0.8); add(sfx, 54.0, sparkle(0.7), 0.5)
# スロット回転(1.9〜3.9)とハテナの溜め(3.9)
t = 1.9
while t < 3.9: add(sfx, t, tick(), 0.5); t += 0.06
add(sfx, 3.9, sting(), 0.9)
# カウントアップ中のコイン音(5.4〜6.9 / 30.5〜31.6 / 35.0〜36.3)
for a, b, step in ((5.4, 6.9, 0.11), (30.5, 31.6, 0.11), (35.0, 36.3, 0.11)):
    t = a; i = 0
    while t < b: add(sfx, t, coin(1600 * 2 ** (i / 14)), 0.35); t += step; i += 1
add(sfx, 44.95, coin(2000), 0.8); add(sfx, 45.25, coin(2500), 0.8)  # コインが 2 枚に
sfx = sfx / max(1.0, np.max(np.abs(sfx)))

# ---------- ミックス ----------
narr = read_wav(os.path.join(OUT, 'narration.wav'))
music = bgm_mod.generate(TOTAL)
n = len(sfx)
narr = np.pad(narr, (0, max(0, n - len(narr))))[:n]; music = np.pad(music, (0, max(0, n - len(music))))[:n]
# ナレーションの包絡 → ダッキング量
hop = SR // 20
rms = np.sqrt(np.mean(narr[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.88)
env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
speech = np.clip(env / 0.06, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.38, 0.085
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 8
gain = np.convolve(gain, np.ones(k) / k, mode='same')
sfx_gain = 0.5 - 0.3 * speech  # 発話中は効果音も控えめに
mixed = narr * 1.0 + music * gain + sfx * sfx_gain
mixed = np.tanh(mixed * 1.05) / np.tanh(1.05)
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
write_wav(MIX, mixed); write_wav(os.path.join(OUT, 'sfx.wav'), sfx); write_wav(os.path.join(OUT, 'bgm.wav'), music)
print('wrote', MIX)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
