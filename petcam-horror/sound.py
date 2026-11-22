# -*- coding: utf-8 -*-
"""環境音・効果音・短いピアノを numpy だけで合成し、ナレーションとミックスして output/mix.wav を書き出す。
シーンのタイミングは output/timeline.json(narrate.py が生成)から読む。外部音源は使わない。
使い方: python3 sound.py
"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
TL = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
TOTAL = TL['total']
N = int(TOTAL * SR)
SC = {s['id']: s for s in TL['scenes']}
rs = np.random.default_rng(11)
tt = np.arange(N) / SR

def read_wav(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
def lp_fast(x, cutoff):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4); return np.fft.irfft(X, len(x)).astype(np.float32)
def bp_fast(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= ((f > lo) & (f < hi)); return np.fft.irfft(X, len(x)).astype(np.float32)
def env_curve(points):
    xs, ys = zip(*points); return np.interp(tt, xs, ys).astype(np.float32)
def add(buf, x, at, gain=1.0):
    s = int(at * SR)
    if s >= len(buf) or s + len(x) <= 0: return
    e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s] * gain
def norm(x): return x / (np.max(np.abs(x)) or 1)
def k_(dur): n = int(dur * SR); return n, np.arange(n) / SR
def S(sid): return SC[sid]['start']
def E(sid): return SC[sid]['end']

amb = np.zeros(N, np.float32)
sfx = np.zeros(N, np.float32)
mus = np.zeros(N, np.float32)

# ---------- カメラのマイク越しの部屋の音 ----------
hiss = norm(bp_fast(rs.standard_normal(N).astype(np.float32), 2000, 9000))
hum = np.sin(2 * np.pi * 100 * tt) * 0.4 + np.sin(2 * np.pi * 200 * tt) * 0.15     # 冷蔵庫・電源のうなり
room = norm(lp_fast(rs.standard_normal(N).astype(np.float32), 250))
# カメラ映像が出ている区間だけ鳴らす(寝室の場面とエンドは静か)
t_notify = S('alert') + 0.15     # 録画を見ている最中に通知
t_live = S('live')
on_cam = env_curve([(0, 1), (S('line') - 0.05, 1), (S('line'), 0), (S('zoom') - 0.02, 0), (S('zoom'), 1), (E('reveal'), 1), (E('reveal') + 0.05, 0.3),
                    (t_live - 0.02, 0.3), (t_live, 1.4), (E('live') - 0.02, 1.4), (E('live'), 0), (TOTAL, 0)])
amb += (hiss * 0.012 + hum * 0.01 + room * 0.03) * on_cam

# 尻尾が床を叩く音(映像の尻尾の振り 4.5Hz の半分くらいで)
def thump(g=1.0):
    n, k = k_(0.08); return (np.sin(2 * np.pi * 90 * k) * np.exp(-k * 60) + rs.standard_normal(n) * np.exp(-k * 120) * 0.2).astype(np.float32) * g
for a, b, rate in [(0.3, E('day1'), 2.25), (S('day3') + 0.2, E('day3'), 2.0), (t_live + 0.1, E('live') - 0.4, 1.75)]:
    t0 = a
    while t0 < b:
        add(sfx, thump(), t0, 0.12 * (0.7 + 0.3 * rs.random())); t0 += 1 / rate + rs.random() * 0.05
# ハッハッという息づかい
def pant(dur):
    n, k = k_(dur); x = bp_fast(rs.standard_normal(n).astype(np.float32), 700, 3500)
    return norm(x) * (np.maximum(0, np.sin(2 * np.pi * 3.2 * k)) ** 2)
add(sfx, pant(E('day1') - 0.5), 0.4, 0.035)
add(sfx, pant(E('day3') - S('day3')), S('day3'), 0.03)

# ---------- 祖母の場面: 静かなピアノ(ハ長調、ゆっくり) ----------
def piano(f, dur=2.5):
    n, k = k_(dur)
    x = sum(np.sin(2 * np.pi * f * h * k) / h ** 1.6 * np.exp(-k * (1.2 + h * 0.6)) for h in range(1, 6))
    return (x * np.minimum(1, k / 0.005)).astype(np.float32)
notes = [(0.0, [261.6, 329.6, 392.0]), (1.6, [220.0, 261.6, 329.6]), (3.2, [174.6, 220.0, 261.6]), (4.8, [196.0, 246.9, 293.7]), (6.4, [261.6, 329.6, 392.0])]
for dt, chord in notes:
    for i, f in enumerate(chord): add(mus, piano(f, 3.0), S('grandma') + 0.3 + dt + i * 0.06, 0.06)
    add(mus, piano(chord[-1] * 2, 2.0), S('grandma') + 0.3 + dt + 0.8, 0.035)
mus *= env_curve([(0, 1), (E('grandma') - 0.4, 1), (E('grandma') + 0.2, 0), (TOTAL, 0)])

# ---------- 友達: 空気が変わる ----------
# 「ねえ」の直前で部屋の音を少し落とし、低いうなりを入れる
fr = next(c for c in TL['cues'] if c['kind'] == 'friend')
# チャットの受信音
for at in [fr['a'] - 0.2, fr['a'] + 0.7, fr['a'] + 2.1]:
    n, k = k_(0.12); add(sfx, (np.sin(2 * np.pi * 1046.5 * k) * np.exp(-k * 30)).astype(np.float32), at, 0.12)
n, k = k_(E('line') - fr['a'] + 0.5)
low = (np.sin(2 * np.pi * 41 * k) + 0.6 * np.sin(2 * np.pi * 43.5 * k)) * np.minimum(1, k / 0.8)
add(amb, low.astype(np.float32), fr['a'] - 0.5, 0.18)

# ---------- 拡大・補正: 操作音と高まるドローン ----------
def beep(f=1800, dur=0.05):
    n, k = k_(dur); return (np.sin(2 * np.pi * f * k) * np.hanning(n)).astype(np.float32)
for j in range(4): add(sfx, beep(1500 + j * 150), S('zoom') + 0.15 + j * 0.32, 0.08)
for j in range(5): add(sfx, beep(900, 0.03), S('zoom') + 1.8 + j * 0.28, 0.07)
z0, z1 = S('zoom'), E('reveal')
swell = env_curve([(0, 0), (fr['a'], 0), (z0, 0.3), (S('reveal'), 1), (E('reveal') - 1.0, 0.8), (E('reveal'), 0), (TOTAL, 0)])
cluster = sum(np.sin(2 * np.pi * f * tt + i) for i, f in enumerate([110, 116.5, 155.6, 233.1, 246.9]))
amb += cluster * swell ** 1.5 * 0.035

# ---------- 男に気づく瞬間 ----------
def hit(dur=3.0, f0=50, bright=1.0):
    n, k = k_(dur)
    boom = np.sin(2 * np.pi * (f0 + 40 * np.exp(-k * 18)) * k) * np.exp(-k * 1.8)
    metal = sum(np.sin(2 * np.pi * f * k) * np.exp(-k * (2 + i)) for i, f in enumerate([311, 467, 733, 1109, 1567]))
    nz = rs.standard_normal(n) * np.exp(-k * 25)
    return (boom * 0.9 + metal * 0.12 * bright + nz * 0.3).astype(np.float32)
add(sfx, hit(3.0, 46, 1.2), S('reveal') + 0.05, 0.6)

# ---------- 寝室: 通知音 → ライブ映像 → 最後に低い衝撃 ----------
def chime():
    out = np.zeros(int(0.7 * SR), np.float32)
    for dt, f in [(0, 1318.5), (0.12, 1760.0)]:
        n, k = k_(0.5); add(out, (np.sin(2 * np.pi * f * k) * np.exp(-k * 7)).astype(np.float32), dt)
    return out
add(sfx, chime(), t_notify, 0.22)
n, k = k_(0.03); add(sfx, (rs.standard_normal(n) * np.exp(-k * 200)).astype(np.float32), t_live - 0.05, 0.15)   # タップ
add(sfx, hit(3.0, 38, 1.6), t_live + 4.5, 0.8)                                                                  # 刃物が光る
# 金属がきらっと鳴る
n, k = k_(1.2); add(sfx, sum(np.sin(2 * np.pi * f * k) * np.exp(-k * 4) for f in [2637, 3951, 5274]).astype(np.float32), t_live + 4.5, 0.05)
n, k = k_(E('live') - t_live)
add(amb, ((np.sin(2 * np.pi * 43 * k) + 0.7 * np.sin(2 * np.pi * 61.7 * k)) * np.minimum(1, k / 0.5)).astype(np.float32), t_live, 0.15)

# ---------- ナレーション ----------
voice = read_wav(os.path.join(OUT, 'narration.wav'))[:N]
voice = np.pad(voice, (0, N - len(voice)))
hop = SR // 20
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for j, v in enumerate(rms): envl[j] = max(v, (envl[j - 1] if j else 0) * 0.9)
envl = np.pad(np.repeat(envl, hop), (0, N - len(envl) * hop))
duck = 1 - 0.4 * np.clip(envl / 0.1, 0, 1)
duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same')

bed = amb * duck + mus * (0.6 + 0.4 * duck)
L = voice * 0.9 + bed + sfx
R = voice * 0.9 + np.roll(bed, int(0.009 * SR)) + sfx
st = np.stack([L, R], 1)
st = st / max(1.0, np.max(np.abs(st)) / 0.97)
with wave.open(os.path.join(OUT, 'mix.wav'), 'wb') as wv:
    wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
    wv.writeframes((st * 32767).astype(np.int16).tobytes())
print('wrote output/mix.wav', TOTAL, 's')
