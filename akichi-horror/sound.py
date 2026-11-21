# -*- coding: utf-8 -*-
"""環境音と効果音を numpy だけで合成し、ナレーションとミックスして output/mix.wav を書き出す。
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
rs = np.random.default_rng(7)
tt = np.arange(N) / SR

def read_wav(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

def lp_fast(x, cutoff):  # FFT ローパス
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4); return np.fft.irfft(X, len(x)).astype(np.float32)
def bp_fast(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= ((f > lo) & (f < hi)); return np.fft.irfft(X, len(x)).astype(np.float32)
def env_curve(points):   # [(秒, 値), ...] を線形補間した包絡
    xs, ys = zip(*points); return np.interp(tt, xs, ys).astype(np.float32)
def add(buf, x, at, gain=1.0):
    s = int(at * SR)
    if s >= len(buf): return
    e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s] * gain
def norm(x): return x / (np.max(np.abs(x)) or 1)

amb = np.zeros(N, np.float32)
sfx = np.zeros(N, np.float32)

# ---------- 環境音 ----------
# 低いドローン(わずかにデチューンした低音 + うなり)
drone = (np.sin(2 * np.pi * 43.65 * tt) + 0.8 * np.sin(2 * np.pi * 44.1 * tt + 1) + 0.35 * np.sin(2 * np.pi * 65.4 * tt)
         + 0.25 * np.sin(2 * np.pi * 92.5 * tt + 0.3 * np.sin(2 * np.pi * 0.11 * tt)))  # 三全音
drone *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt)
# 風(ローパスしたノイズに、ゆっくり揺れる音量)
wind = lp_fast(rs.standard_normal(N).astype(np.float32), 380)
wind = norm(wind) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * tt + 2) ** 2)
# 夜の虫(コオロギ風の短いチャープ)
crick = np.zeros(N, np.float32)
for base_f, rate, ph in [(4400, 2.1, 0.0), (4950, 1.7, 0.4), (3900, 2.6, 0.9)]:
    t0 = ph
    while t0 < TOTAL:
        n = int(0.11 * SR); k = np.arange(n) / SR
        chirp = np.sin(2 * np.pi * base_f * k) * (np.sin(2 * np.pi * 45 * k) > 0) * np.hanning(n)
        add(crick, chirp.astype(np.float32), t0, 0.5 + 0.5 * rs.random())
        t0 += 1 / rate + rs.random() * 0.25
def scene_mask(ids, fade=0.25):
    m = np.zeros(N, np.float32)
    for sid in ids:
        a, b = SC[sid]['start'], SC[sid]['end']
        m = np.maximum(m, np.clip(np.minimum((tt - a) / fade + 1, (b - tt) / fade + 1), 0, 1))
    return m
indoor = scene_mask(['clock', 'neighbor', 'scare'])
crick_g = (1 - indoor) * (1 - scene_mask(['approach', 'window']) * 0.7)
amb += drone * 0.20 + wind * 0.10 * (1 - indoor * 0.7) + crick * 0.035 * crick_g

# 終盤に向けてドローンを持ち上げる(窓のシーンで最大 → ジャンプスケア直前に消す)
w = SC['window']; s = SC['scare']; e = SC['end']
swell = env_curve([(0, 0), (w['start'], 0), (s['start'] - 0.05, 1), (s['start'], 0), (TOTAL, 0)])
cluster = sum(np.sin(2 * np.pi * f * tt + i) for i, f in enumerate([233.1, 246.9, 261.6, 349.2, 370.0]))
cluster *= 1 + 0.3 * np.sin(2 * np.pi * 5.5 * tt)
amb += cluster * swell ** 2 * 0.05
# ジャンプスケア後の無音 → エンディングで低音だけ戻す
silence = env_curve([(0, 1), (s['start'] + 0.9, 1), (s['end'], 0), (e['start'] + 0.6, 0), (e['start'] + 3, 0.8), (TOTAL - 1.2, 0.8), (TOTAL, 0)])
amb *= silence

# ---------- 効果音 ----------
def hit(dur=3.0, f0=55, bright=1.0):
    """低いドンという衝撃音 + 金属的な倍音"""
    n = int(dur * SR); k = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (f0 + 40 * np.exp(-k * 18)) * k) * np.exp(-k * 1.8)
    metal = sum(np.sin(2 * np.pi * f * k) * np.exp(-k * (2 + i)) for i, f in enumerate([311, 467, 733, 1109, 1567]))
    nz = rs.standard_normal(n) * np.exp(-k * 25)
    return (boom * 0.9 + metal * 0.12 * bright + nz * 0.3).astype(np.float32)
def riser(dur, f_from, f_to):
    n = int(dur * SR); k = np.arange(n) / SR
    f = f_from * (f_to / f_from) ** (k / dur); ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * (k / dur) ** 2).astype(np.float32)
def glitch_burst(dur=0.12):
    n = int(dur * SR); x = rs.standard_normal(n).astype(np.float32)
    x = np.repeat(x[::12], 12)[:n]                     # ビットクラッシュ風
    return x * np.hanning(n) * 0.5
def tick():
    n = int(0.03 * SR); k = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2400 * k) * np.exp(-k * 300) + rs.standard_normal(n) * np.exp(-k * 400) * 0.3).astype(np.float32)
def thump(f=50):
    n = int(0.25 * SR); k = np.arange(n) / SR
    return (np.sin(2 * np.pi * (f + 30 * np.exp(-k * 40)) * k) * np.exp(-k * 18)).astype(np.float32)
def whoosh(dur=0.7):
    n = int(dur * SR); x = rs.standard_normal(n).astype(np.float32)
    x = bp_fast(x, 300, 2500) * np.sin(np.linspace(0, np.pi, n)) ** 2
    return norm(x)

# シーン頭のノイズ(映像のグリッチと同期)
for sc in TL['scenes'][1:]:
    if sc['id'] not in ('end',):
        add(sfx, glitch_burst(0.12), sc['start'], 0.12)
# タイトル: 低い衝撃音
add(sfx, hit(3.5, 41, 0.6), 0.3, 0.55)
# 時計: 秒針 → 2:00 で衝撃音
c = SC['clock']['start']
for i in range(2): add(sfx, tick(), c + 0.3 + i * 0.5, 0.35)
add(sfx, hit(3.0, 48, 1.0), c + 1.3, 0.75); add(sfx, glitch_burst(0.25), c + 1.3, 0.25)
# 人影が現れる: 不協和な高音のうねり
f = SC['figure']['start']
n = int(3.5 * SR); k = np.arange(n) / SR
sw = sum(np.sin(2 * np.pi * fr * k) for fr in [880, 932.3, 1318.5]) * np.sin(np.pi * k / 3.5) ** 2
add(sfx, sw.astype(np.float32), f + 0.4, 0.035); add(sfx, glitch_burst(0.3), f + 0.6, 0.2)
# 「空き地? そんなもの…」: 耳鳴り
a = SC['answer']
n = int((a['end'] - a['start']) * SR); k = np.arange(n) / SR
ring = np.sin(2 * np.pi * 5200 * k) * np.minimum(1, k / 1.5) * np.minimum(1, (k[-1] - k) / 0.2)
add(sfx, ring.astype(np.float32), a['start'], 0.02)
# 近づく: 心音(映像の脈動と同期: u = (0.25 + i) / 1.25 で最大)
ap = SC['approach']; d = ap['end'] - ap['start']
i = 0
while True:
    u = (0.25 + i) / 1.25
    if u > d: break
    add(sfx, thump(52), ap['start'] + u - 0.04, 0.55); add(sfx, thump(46), ap['start'] + u + 0.2, 0.35)
    i += 1
add(sfx, hit(2.5, 60, 1.2), ap['start'] + d * 0.48, 0.5)          # 同じ服だと気づく瞬間
# 足音(砂利)
for j in range(6):
    n = int(0.09 * SR); x = bp_fast(rs.standard_normal(n).astype(np.float32), 900, 5000) * np.exp(-np.arange(n) / SR * 40)
    add(sfx, x, ap['start'] + 0.4 + j * 0.62, 0.25)
# 振り返る: ヒュッ
add(sfx, whoosh(0.7), w['start'] + 0.05, 0.35)
add(sfx, riser(w['end'] - w['start'] - 0.9, 80, 1400), w['start'] + 0.9, 0.12)
# ジャンプスケア: 大きな衝撃音 + 金切り声のような FM ノイズ
add(sfx, hit(2.2, 38, 2.0), s['start'], 1.0)
n = int(0.95 * SR); k = np.arange(n) / SR
scream = np.sin(2 * np.pi * 1450 * k + 9 * np.sin(2 * np.pi * 97 * k)) * np.minimum(1, k / 0.02) * np.minimum(1, (k[-1] - k) / 0.05)
scream += rs.standard_normal(n) * 0.4
add(sfx, bp_fast(scream.astype(np.float32), 600, 7000), s['start'], 0.35)
# エンディング: 囁きの後、遠くで窓がきしむ
n = int(1.4 * SR); k = np.arange(n) / SR
creak = np.sin(2 * np.pi * np.cumsum(180 + 80 * np.sin(2 * np.pi * 1.3 * k) + 40 * rs.standard_normal(n).cumsum() / np.sqrt(n)) / SR)
creak *= (np.sin(2 * np.pi * 23 * k) > 0.3) * np.sin(np.pi * k / 1.4)
add(sfx, bp_fast(creak.astype(np.float32), 200, 3000), TOTAL - 2.2, 0.12)

# ---------- ナレーション(軽いリバーブ) ----------
voice = read_wav(os.path.join(OUT, 'narration.wav'))[:N]
voice = np.pad(voice, (0, N - len(voice)))
rev = np.zeros_like(voice)
for dly, g in [(0.043, 0.3), (0.071, 0.22), (0.113, 0.16), (0.167, 0.1), (0.241, 0.06)]:
    d_ = int(dly * SR); rev[d_:] += voice[:-d_] * g
voice_w = voice + lp_fast(rev, 3500) * 0.8

# 発話中は環境音を少し下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for j, v in enumerate(rms): envl[j] = max(v, (envl[j - 1] if j else 0) * 0.9)
envl = np.pad(np.repeat(envl, hop), (0, N - len(envl) * hop))
duck = 1 - 0.45 * np.clip(envl / 0.1, 0, 1)
duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same')

mix = voice_w * 0.95 + amb * duck * 0.9 + sfx * 0.8
# 簡易ステレオ: 環境音にだけ左右の差をつける
amb_r = np.roll(amb * duck, int(0.011 * SR))
L = mix; R = voice_w * 0.95 + amb_r * 0.9 + sfx * 0.8
st = np.stack([L, R], 1)
st = st / max(1.0, np.max(np.abs(st)) / 0.97)
with wave.open(os.path.join(OUT, 'mix.wav'), 'wb') as wv:
    wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
    wv.writeframes((st * 32767).astype(np.int16).tobytes())
print('wrote output/mix.wav', TOTAL, 's')
