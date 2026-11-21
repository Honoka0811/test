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
    if s >= len(buf): return
    e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s] * gain
def norm(x): return x / (np.max(np.abs(x)) or 1)
def k_(dur): n = int(dur * SR); return n, np.arange(n) / SR
def S(sid): return SC[sid]['start']
def D(sid): return SC[sid]['end'] - SC[sid]['start']

amb = np.zeros(N, np.float32)
sfx = np.zeros(N, np.float32)

# ---------- 環境音(夜の屋外) ----------
drone = (np.sin(2 * np.pi * 43.65 * tt) + 0.8 * np.sin(2 * np.pi * 44.1 * tt + 1) + 0.35 * np.sin(2 * np.pi * 65.4 * tt)
         + 0.25 * np.sin(2 * np.pi * 92.5 * tt + 0.3 * np.sin(2 * np.pi * 0.11 * tt)))
drone *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * tt)
wind = norm(lp_fast(rs.standard_normal(N).astype(np.float32), 380)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * tt + 2) ** 2)
crick = np.zeros(N, np.float32)
for base_f, rate, ph in [(4400, 2.1, 0.0), (4950, 1.7, 0.4), (3900, 2.6, 0.9)]:
    t0 = ph
    while t0 < TOTAL:
        n, k = k_(0.11)
        add(crick, (np.sin(2 * np.pi * base_f * k) * (np.sin(2 * np.pi * 45 * k) > 0) * np.hanning(n)).astype(np.float32), t0, 0.5 + 0.5 * rs.random())
        t0 += 1 / rate + rs.random() * 0.25
# 盛り上げ: 電話の声のあたりから不協和音がじわじわ。「振り向いたら」の直前で全部消える
swell = env_curve([(0, 0), (S('phone'), 0), (S('sweep') + D('sweep'), 1), (S('behind') + 0.6, 1), (S('behind') + 0.7, 0), (TOTAL, 0)])
cluster = sum(np.sin(2 * np.pi * f * tt + i) for i, f in enumerate([233.1, 246.9, 261.6, 349.2, 370.0]))
cluster *= 1 + 0.3 * np.sin(2 * np.pi * 5.5 * tt)
# 全体の音量: 「振り向いたら」の前で無音に落とす → エンドで低音だけ戻す
b = S('behind'); e = S('end')
master = env_curve([(0, 1), (b + 0.6, 1), (b + 0.75, 0.0), (e, 0.0), (e + 0.4, 0.5), (TOTAL - 0.6, 0.5), (TOTAL, 0)])
amb += (drone * 0.22 + wind * 0.10 + crick * 0.03) * master + cluster * swell ** 2 * 0.045

# ---------- 効果音 ----------
def hit(dur=3.0, f0=55, bright=1.0):
    n, k = k_(dur)
    boom = np.sin(2 * np.pi * (f0 + 40 * np.exp(-k * 18)) * k) * np.exp(-k * 1.8)
    metal = sum(np.sin(2 * np.pi * f * k) * np.exp(-k * (2 + i)) for i, f in enumerate([311, 467, 733, 1109, 1567]))
    nz = rs.standard_normal(n) * np.exp(-k * 25)
    return (boom * 0.9 + metal * 0.12 * bright + nz * 0.3).astype(np.float32)
def glitch_burst(dur=0.12):
    n, _ = k_(dur); x = rs.standard_normal(n).astype(np.float32)
    return np.repeat(x[::12], 12)[:n] * np.hanning(n) * 0.5
def tel(x): return bp_fast(x, 300, 3400)

# 冒頭: いきなり低い衝撃音
add(sfx, hit(3.0, 41, 0.7), 0.05, 0.5)
# 爪で削る: 指の往復(sin(u*15))の半周期ごとにガリッ
u = 0.0; i = 0; d = D('scratch') - 0.35
while u < d:
    n, k = k_(0.17); x = bp_fast(rs.standard_normal(n).astype(np.float32), 1800, 9000)
    x *= np.sin(np.pi * k / 0.17) ** 0.5 * (0.6 + 0.4 * np.sin(2 * np.pi * 70 * k))
    add(sfx, norm(x), S('scratch') + u, 0.18 * (0.7 + 0.3 * rs.random()))
    i += 1; u = i * np.pi / 15
# 番号に気づく瞬間
add(sfx, hit(2.5, 48, 1.2), S('reveal') + 0.9, 0.6); add(sfx, glitch_burst(0.2), S('reveal') + 0.9, 0.2)
# 発信: プッシュ音 → 呼び出し音(400Hz を 16Hz で断続、1秒鳴って2秒休み)
for j, (f1, f2) in enumerate([(941, 1336), (697, 1209), (852, 1477), (770, 1209)]):
    n, k = k_(0.07); add(sfx, (np.sin(2 * np.pi * f1 * k) + np.sin(2 * np.pi * f2 * k)).astype(np.float32) * np.hanning(n), S('call') + 0.5 + j * 0.09, 0.05)
for j in range(2):
    n, k = k_(1.0); x = np.sin(2 * np.pi * 400 * k) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 16 * k)))
    add(sfx, tel(x.astype(np.float32)), S('call') + 1.0 + j * 2.0, 0.12)
# 相手が出る: カチッ
n, k = k_(0.03); add(sfx, (rs.standard_normal(n) * np.exp(-k * 200)).astype(np.float32), S('answer') + 0.1, 0.4)
# 通話中の回線ノイズ
a0, a1 = S('answer') + 0.1, S('behind') + 0.5
n = int((a1 - a0) * SR); line = tel(rs.standard_normal(n).astype(np.float32)); line = norm(line) * (0.7 + 0.3 * np.sin(np.arange(n) / SR * 2 * np.pi * 0.5))
add(sfx, line, a0, 0.025)
add(sfx, glitch_burst(0.3), S('phone'), 0.22)
# 空き地を探す: 砂利の足音、地面のスマホのバイブ、画面が読めた瞬間の衝撃音
for j in range(5):
    n, k = k_(0.09); x = bp_fast(rs.standard_normal(n).astype(np.float32), 900, 5000) * np.exp(-k * 40)
    add(sfx, norm(x), S('sweep') + 0.2 + j * 0.55, 0.18)
for j in range(4):
    n, k = k_(0.4); x = np.sin(2 * np.pi * 160 * k) * np.sign(np.sin(2 * np.pi * 40 * k)) * np.sin(np.pi * k / 0.4)
    add(sfx, x.astype(np.float32), S('sweep') + 1.0 + j * 0.9, 0.04)
add(sfx, hit(2.5, 52, 1.3), S('sweep') + D('sweep') - 1.6, 0.55)
# 振り向いたら: 終話音(プー、プー)→ 無音 → 耳元の息 → 声 → 最後に衝撃音
for j in range(2):
    n, k = k_(0.25); add(sfx, tel(np.sin(2 * np.pi * 400 * k).astype(np.float32)) * np.hanning(n) ** 0.2, b + 0.05 + j * 0.35, 0.08)
n, k = k_(1.0); breath = bp_fast(rs.standard_normal(n).astype(np.float32), 500, 4000) * np.sin(np.pi * k / 1.0) ** 2
add(sfx, norm(breath), b + 0.5, 0.05)
add(sfx, hit(2.2, 38, 1.8), e - 0.3, 0.85); add(sfx, glitch_burst(0.3), e - 0.3, 0.35)
# エンド: 視聴者のスマホが震える(ブーッ、ブーッ)
t0 = e + 0.85
while t0 < TOTAL - 0.4:
    n, k = k_(0.45); x = np.sin(2 * np.pi * 150 * k) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 30 * k))) * np.minimum(1, np.minimum(k, k[-1] - k) / 0.02)
    add(sfx, x.astype(np.float32), t0, 0.1); t0 += 0.75

# ---------- ナレーション ----------
voice = read_wav(os.path.join(OUT, 'narration.wav'))[:N]
voice = np.pad(voice, (0, N - len(voice)))
rev = np.zeros_like(voice)
for dly, g in [(0.031, 0.22), (0.057, 0.16), (0.089, 0.1)]:
    d_ = int(dly * SR); rev[d_:] += voice[:-d_] * g
voice_w = voice + lp_fast(rev, 3500) * 0.6

hop = SR // 20
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for j, v in enumerate(rms): envl[j] = max(v, (envl[j - 1] if j else 0) * 0.9)
envl = np.pad(np.repeat(envl, hop), (0, N - len(envl) * hop))
duck = 1 - 0.45 * np.clip(envl / 0.1, 0, 1)
duck = np.convolve(duck, np.ones(SR // 10) / (SR // 10), mode='same')

# 耳元の声(behind)だけ左に寄せて「後ろにいる」感じを出す
pan_l = np.ones(N, np.float32); pan_r = np.ones(N, np.float32)
cb = next(c for c in TL['cues'] if c['kind'] == 'close')
m = (tt >= cb['a'] - 0.1) & (tt <= cb['b'] + 0.3)
pan_l[m] = 1.25; pan_r[m] = 0.55
L = voice_w * 0.95 * pan_l + amb * duck * 0.9 + sfx * 0.8
R = voice_w * 0.95 * pan_r + np.roll(amb * duck, int(0.011 * SR)) * 0.9 + sfx * 0.8
st = np.stack([L, R], 1)
st = st / max(1.0, np.max(np.abs(st)) / 0.97)
with wave.open(os.path.join(OUT, 'mix.wav'), 'wb') as wv:
    wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
    wv.writeframes((st * 32767).astype(np.int16).tobytes())
print('wrote output/mix.wav', TOTAL, 's')
