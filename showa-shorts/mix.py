# -*- coding: utf-8 -*-
"""BGM(昭和歌謡風・自作合成)と効果音を timeline.json に合わせて生成し、
ナレーション中は BGM を自動で下げてミックス → 無音動画に合成する。
出力: output/bgm.wav, output/sfx.wav, output/mix.wav, output/showa_best5.mp4
"""
import os, json, wave, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
TL = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
TOTAL = TL['total']; N = int(TOTAL * SR)
SC = TL['scenes']
rng = np.random.default_rng(1964)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, t, x, g=1.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0: return
    a = max(0, -i); e = min(len(buf), i + len(x))
    buf[max(i, 0):e] += g * x[a:a + e - max(i, 0)]
def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, a):                      # 1 次ローパス(a 小さいほどこもる)
    from scipy.signal import lfilter
    return lfilter([a], [1, a - 1], x).astype(np.float32)
def hp(x, a=0.95):
    from scipy.signal import lfilter
    return lfilter([a, -a], [1, -a], x).astype(np.float32)
def noise(d): return rng.standard_normal(int(d * SR)).astype(np.float32)
def norm(x, p=1.0): return x / (np.max(np.abs(x)) + 1e-9) * p

# ---------------- 楽器 ----------------
def kick():
    t = tt(0.35); f = 45 + 95 * np.exp(-t / 0.04)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)).astype(np.float32)
def snare():
    t = tt(0.22)
    return (0.7 * hp(noise(0.22), 0.7) * np.exp(-t / 0.07) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)).astype(np.float32)
def hat(open_=False):
    d = 0.25 if open_ else 0.05; t = tt(d)
    return (hp(hp(noise(d), 0.9), 0.9) * np.exp(-t / (0.09 if open_ else 0.018))).astype(np.float32)
def crash():
    t = tt(2.2); return (hp(noise(2.2), 0.85) * np.exp(-t / 0.7)).astype(np.float32)
def saw(f, d, det=(-0.006, 0, 0.006)):
    t = tt(d); return sum(2 * ((f * (1 + e) * t + rng.random()) % 1) - 1 for e in det).astype(np.float32) / len(det)
def bass(n, d):
    t = tt(d); f = midi(n)
    x = 0.8 * np.sin(2 * np.pi * f * t) + 0.35 * lp(saw(f, d, (0,)), 0.12)
    return (x * np.minimum(1, t / 0.005) * np.exp(-t / 0.5) * np.minimum(1, (d - t) / 0.02)).astype(np.float32)
def brass(notes, d):               # ブラス風スタブ(デチューンしたノコギリ波 + フィルター開閉)
    t = tt(d); x = sum(saw(midi(n), d) for n in notes)
    x = lp(x, 0.18) * 0.7 + lp(x, 0.5) * 0.3 * np.exp(-t / 0.08)
    return (x * np.minimum(1, t / 0.012) * np.minimum(1, (d - t) / 0.03)).astype(np.float32)
def organ(notes, d):
    t = tt(d); x = np.zeros_like(t)
    for n in notes:
        f = midi(n)
        for h, a in ((1, 1), (2, .5), (3, .25), (4, .15)): x += a * np.sin(2 * np.pi * f * h * t * (1 + 0.003 * np.sin(2 * np.pi * 5.5 * t)))
    return (x * np.minimum(1, t / 0.05) * np.minimum(1, (d - t) / 0.08)).astype(np.float32)
def lead(n, d):                    # 歌謡曲のメロ担当: ビブラート付き矩形波
    t = tt(d); f = midi(n) * (1 + 0.006 * np.sin(2 * np.pi * 5.8 * t) * np.minimum(1, t / 0.2))
    ph = np.cumsum(f) / SR; x = np.sign(np.sin(2 * np.pi * ph)) * 0.5 + 0.5 * np.sin(2 * np.pi * ph)
    return (lp(x.astype(np.float32), 0.25) * np.minimum(1, t / 0.01) * np.minimum(1, (d - t) / 0.03)).astype(np.float32)

BPM = 128; B = 60 / BPM; BAR = 4 * B
# Am - F - G - C / Am - F - E7 - Am(歌謡曲の王道進行)
PROG = [(57, [57, 60, 64]), (53, [53, 57, 60]), (55, [55, 59, 62]), (48, [55, 60, 64]),
        (57, [57, 60, 64]), (53, [53, 57, 60]), (52, [52, 56, 59, 62]), (57, [57, 60, 64])]
# 1 小節ごとのメロディ(拍, 長さ, 音)
MEL = [
    [(0, 1.5, 76), (1.5, .5, 74), (2, 1, 72), (3, 1, 69)],
    [(0, 1, 72), (1, 1, 74), (2, 2, 76)],
    [(0, 1.5, 74), (1.5, .5, 72), (2, 1, 71), (3, 1, 67)],
    [(0, 3, 72), (3, .5, 74), (3.5, .5, 76)],
    [(0, 1.5, 81), (1.5, .5, 79), (2, 1, 76), (3, 1, 74)],
    [(0, 1, 72), (1, 1, 74), (2, 1.5, 76), (3.5, .5, 72)],
    [(0, 1, 71), (1, 1, 74), (2, 1, 76), (3, 1, 80)],
    [(0, 4, 81)],
]

def section(t):
    for s in SC:
        if s['start'] <= t < s['end']: return s
    return SC[-1]

drums = np.zeros(N, np.float32); bas = np.zeros(N, np.float32); chords = np.zeros(N, np.float32)
mel = np.zeros(N, np.float32); fx = np.zeros(N, np.float32)
K, S = kick(), snare()
tease = next(s for s in SC if s['kind'] == 'tease')
r1 = next(s for s in SC if s.get('rank') == 1)
outro_end = TOTAL - 1.4               # 最後の決めの一発

start = 0.3                           # テレビが点いてから演奏開始
nb = int((TOTAL - start) / BAR) + 2
for b in range(nb):
    t0 = start + b * BAR
    if t0 >= outro_end: break
    sec = section(t0 + 0.01)
    if tease['start'] - BAR * 0.5 < t0 < r1['start']: continue      # 第1位前はタメ(下で別処理)
    key = 2 if t0 >= r1['start'] - 0.01 else 0                       # 第1位から全音転調
    root, ch = PROG[b % 8]
    for beat in range(4):
        tb = t0 + beat * B
        if tb >= outro_end: break
        add(drums, tb, K, 1.0 if beat in (0, 2) else 0.0)
        if beat in (1, 3): add(drums, tb, S, 0.75)
        add(drums, tb, hat(), 0.25); add(drums, tb + B / 2, hat(beat == 3), 0.32)
        # ウォーキングベース: ルート→5度→オクターブ→経過音
        bn = [root - 12, root - 5, root, root - 10][beat] + key
        add(bas, tb, bass(bn - 12, B * 0.9), 0.9)
        # 裏拍のブラススタブ(ズンチャッ)
        add(chords, tb + B / 2, brass([n + key for n in ch], B * 0.38), 0.5)
    add(chords, t0, organ([n + key - 12 for n in ch], BAR), 0.12)
    for (bt, d, n) in MEL[b % 8]:
        add(mel, t0 + bt * B, lead(n + key, d * B * 0.95), 0.55)

# タメ: スネアのロール(クレッシェンド)+ ベースのペダル
ts, te = tease['start'] - 0.1, r1['start']
t = ts
while t < te - 0.05:
    p = (t - ts) / (te - ts)
    add(drums, t, S, 0.15 + 0.6 * p ** 1.5)
    t += 0.12 - 0.07 * p                # だんだん細かく
for k in range(int((te - ts) / B)):
    add(bas, ts + k * B, bass(45 - 12, B * 0.9), 0.6)
# 第1位: クラッシュ
add(drums, r1['start'], crash(), 0.8); add(drums, r1['start'], K, 1.2)
# エンディングの決め(Am + 全音 = Bm の一発)
add(drums, outro_end, crash(), 0.9); add(drums, outro_end, K, 1.2)
add(chords, outro_end, brass([59, 62, 66, 71], 1.2), 1.0)
add(bas, outro_end, bass(35, 1.2), 1.0)

music = 0.9 * norm(drums) + 0.65 * norm(bas) + 0.45 * norm(chords) + 0.32 * norm(mel)
# 簡易リバーブ
def comb(x, d, g):
    y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += g * y[s - d:e - d]
    return y
music = music + 0.12 * sum(comb(music, d, g) for d, g in ((1553, .6), (2251, .55), (3203, .5))) / 3
# 古いラジオ風: 高域を少し丸める
music = lp(music, 0.55)
music = norm(music, 0.9)

# ---------------- 効果音 ----------------
def whoosh(d=0.35):
    t = tt(d); x = noise(d); env = np.sin(np.pi * t / d) ** 2
    return (lp(x, 0.08) * env).astype(np.float32)
def boom():
    t = tt(0.9); f = 38 + 70 * np.exp(-t / 0.06)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.3) + 0.4 * lp(noise(0.9), 0.1) * np.exp(-t / 0.08)).astype(np.float32)
def ding(n=88, d=0.6):
    t = tt(d); return ((np.sin(2 * np.pi * midi(n) * t) + 0.3 * np.sin(2 * np.pi * midi(n + 12) * t)) * np.exp(-t / 0.18)).astype(np.float32)
def pop():
    t = tt(0.12); f = 900 * np.exp(-t / 0.02) + 300
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03)).astype(np.float32)
def click():
    t = tt(0.05); return (hp(noise(0.05), 0.6) * np.exp(-t / 0.006) + np.sin(2 * np.pi * 2500 * t) * np.exp(-t / 0.01) * 0.6).astype(np.float32)
def bell(d=1.6):                  # 黒電話のベル(ジリリリ)
    t = tt(d); car = np.sin(2 * np.pi * 2350 * t) + 0.6 * np.sin(2 * np.pi * 3100 * t)
    am = (np.sin(2 * np.pi * 22 * t) > 0).astype(np.float32)
    return (lp((car * am).astype(np.float32), 0.4) * np.minimum(1, (d - t) / 0.05)).astype(np.float32)
def static(d):
    return (hp(noise(d), 0.8) * 0.6).astype(np.float32)
def chime():                     # 学校のチャイム(キーンコーンカーンコーン)
    x = np.zeros(int(2.4 * SR), np.float32)
    for i, n in enumerate([76, 72, 74, 67]):
        t = tt(1.2); s = (np.sin(2 * np.pi * midi(n) * t) + 0.25 * np.sin(2 * np.pi * midi(n) * 2.76 * t)) * np.exp(-t / 0.5)
        add(x, i * 0.42, s.astype(np.float32))
    return x

sfx = np.zeros(N, np.float32)
add(sfx, 0.0, static(0.3), 0.35); add(sfx, 0.22, click(), 0.8)
hook = SC[0]
add(sfx, hook['lines'][0]['start'] + 0.1, boom(), 0.7)                     # 「昭和」ドン
l1 = hook['lines'][0]; add(sfx, l1['start'] + (l1['end'] - l1['start']) * 0.42, boom(), 0.5)   # 大炎上
l2 = hook['lines'][1]
for i in range(5): add(sfx, l2['start'] + 0.7 + i * 0.22, pop(), 0.5)      # ?カード
for s in SC[1:]:
    add(sfx, s['start'] - 0.02, static(0.18), 0.25)                          # VHS グリッチ
for s in SC:
    if s['kind'] != 'rank': continue
    add(sfx, s['start'] - 0.3, whoosh(), 0.5); add(sfx, s['start'] + 0.02, boom(), 1.0)
    L2 = s['lines'][1]
    add(sfx, L2['start'] - 0.1, ding(), 0.35)                                # 情報カード ピコン
    add(sfx, L2['start'] + (L2['end'] - L2['start']) * 0.55, pop(), 0.6)    # スタンプ
    if s['rank'] == 3:
        for k in range(4): add(sfx, L2['start'] + k / 3, click(), 0.7)       # 改札鋏 カチッ
    if s['rank'] == 2:
        add(sfx, s['start'] + 0.5, bell(1.7), 0.12)                          # 黒電話
    if s['rank'] == 1:
        add(sfx, s['end'] - 2.3, chime(), 0.35)                              # 学校のチャイム
out = SC[-1]
for i in range(5): add(sfx, out['start'] + 1.4 + i * 0.16, click(), 0.4)   # チェック
add(sfx, out['lines'][1]['start'] - 0.1, pop(), 0.6)

# ---------------- ミックス(ナレーション優先のダッキング) ----------------
with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    nar = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
nar = np.pad(nar, (0, max(0, N - len(nar))))[:N]
hop = SR // 50
rms = np.sqrt(np.mean(np.pad(nar, (0, -len(nar) % hop)).reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.96)
env = np.repeat(env, hop)[:N]
speech = np.clip(env / 0.08, 0, 1)
gain = 0.55 - (0.55 - 0.2) * speech
gain = np.convolve(gain, np.ones(SR // 20) / (SR // 20), mode='same')
mix = nar * 1.0 + music * gain + sfx * 0.55
mix *= np.minimum(1, (N - np.arange(N)) / (0.6 * SR))      # 最後 0.6 秒フェード
mix = np.tanh(mix * 1.1) / np.tanh(1.1)                  # 軽いソフトクリップ
for name, x in (('bgm', music), ('sfx', sfx), ('mix', mix)):
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
dst = os.path.join(OUT, 'showa_best5.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'video_silent.mp4'), '-i', os.path.join(OUT, 'mix.wav'),
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
