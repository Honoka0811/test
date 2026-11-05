# -*- coding: utf-8 -*-
"""BGM と効果音をプログラムで合成し(外部音源なし・権利フリー)、ナレーションとミックスして動画に合成する。
BGM: Aマイナー / 128BPM のアップテンポ(Am–F–C–G)。
  - 10位〜4位: キック4つ打ち + クラップ + 16分ハイハット + 裏拍ベース + アルペジオ
  - TOP3 発表前: リズムが抜けてドラムロールとライザーで「ため」→ 発表の瞬間にクラッシュで復帰
  - 1位発表後: ブラス風のコードスタブを追加して最高潮に
効果音: 順位の叩きつけ(シュッ+ドン)、人口カウンター完了のチャイム、TOP3のドラムロール・クラッシュ
使い方: python3 mix.py [入力mp4] [出力mp4]
"""
import os, sys, json, re, wave, subprocess
import numpy as np
from scipy.signal import lfilter, butter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'prewar_population_top10.mp4')
SR = 48000
BPM = 128
BEAT = 60 / BPM
BAR = BEAT * 4

TL = json.loads(re.search(r'window\.TIMELINE=(.*);\s*$', open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read(), re.S).group(1))
TOTAL = TL['total']
SC = {s['id']: s for s in TL['scenes']}
N = int(TOTAL * SR)
rng = np.random.default_rng(1940)


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, fc, order=2): b, a = butter(order, fc / (SR / 2)); return lfilter(b, a, x).astype(np.float32)
def hp(x, fc, order=2): b, a = butter(order, fc / (SR / 2), 'high'); return lfilter(b, a, x).astype(np.float32)
def add(buf, t0, sig, g=1.0):
    s = int(t0 * SR)
    if s >= len(buf): return
    if s < 0: sig = sig[-s:]; s = 0
    e = min(s + len(sig), len(buf)); buf[s:e] += sig[:e - s] * g


# ---------- 音色 ----------
def kick():
    t = tt(0.4); f = 45 + 110 * np.exp(-t / 0.045)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    x[:200] += rng.standard_normal(200) * 0.3 * np.linspace(1, 0, 200)
    return np.tanh(x * 1.6).astype(np.float32)

def clap():
    t = tt(0.25); n = rng.standard_normal(len(t))
    env = np.exp(-t / 0.07)
    for d in (0.0, 0.012, 0.024): env += 0.6 * np.exp(-np.maximum(t - d, 0) / 0.008) * (t >= d)
    return hp(lp(n * env, 5000), 900) * 0.6

def hat(open_=False):
    t = tt(0.25 if open_ else 0.05)
    return hp(rng.standard_normal(len(t)), 7500) * np.exp(-t / (0.08 if open_ else 0.014)).astype(np.float32)

def saw(f, d, nh=12):
    t = tt(d); x = np.zeros(len(t), np.float32)
    for h in range(1, nh + 1):
        if f * h > 14000: break
        x += np.sin(2 * np.pi * f * h * t) / h
    return x

def bass(n, d):
    x = saw(midi(n), d, 8) + 0.5 * np.sin(2 * np.pi * midi(n - 12) * tt(d))
    env = np.minimum(1, tt(d) / 0.005) * np.exp(-tt(d) / 0.18)
    return lp(x * env, 900)

def pluck(n, d=0.35):
    t = tt(d); f = midi(n)
    x = (np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * 2 * f * t) * 0.3) * np.exp(-t / 0.09)
    return lp(x.astype(np.float32), 4200)

def pad(notes, d):
    x = sum(saw(midi(n) * (1 + det), d, 10) for n in notes for det in (-0.003, 0.003))
    env = np.minimum(1, tt(d) / 0.3) * np.minimum(1, (d - tt(d)) / 0.3)
    return lp(x * env, 1800) / (len(notes) * 2)

def stab(notes):
    d = 0.32; x = sum(saw(midi(n) * (1 + det), d, 14) for n in notes for det in (-0.006, 0.006))
    env = np.minimum(1, tt(d) / 0.004) * np.exp(-tt(d) / 0.12)
    return lp(x * env, 3500) / len(notes)

def crash():
    t = tt(2.2); x = hp(rng.standard_normal(len(t)), 4000) * np.exp(-t / 0.7)
    return x.astype(np.float32)

def whoosh(d=0.32):
    t = tt(d); n = rng.standard_normal(len(t)).astype(np.float32)
    # 上昇するバンドパス風(ローパスとハイパスのカットオフを時間で動かす代わりに区間ごとに処理)
    out = np.zeros_like(n); seg = len(n) // 8
    for i in range(8):
        fc = 600 + 5000 * (i / 7) ** 2
        s = slice(i * seg, (i + 1) * seg if i < 7 else len(n))
        out[s] = lp(hp(n[s], fc * 0.4), fc)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return out * env

def boom():
    t = tt(0.9); f = 32 + 70 * np.exp(-t / 0.08)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    x += lp(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.05) * 0.5
    return np.tanh(x * 1.4).astype(np.float32)

def chime():
    t = tt(0.9)
    x = sum(np.sin(2 * np.pi * midi(n) * t) * g for n, g in ((93, 1), (100, 0.6), (105, 0.35)))
    return (x * np.exp(-t / 0.25) * np.minimum(1, t / 0.003)).astype(np.float32)

def tick():
    t = tt(0.03)
    return (np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.006)).astype(np.float32)

def drumroll(d):
    buf = np.zeros(int(d * SR) + SR // 4, np.float32); t = 0.0
    while t < d:
        k = t / d; iv = 0.085 - 0.05 * k  # だんだん速く
        n = rng.standard_normal(int(0.08 * SR))
        s = hp(lp(n, 6000), 400) * np.exp(-tt(0.08) / 0.03) * (0.35 + 0.65 * k)
        add(buf, t, s.astype(np.float32)); t += iv
    return buf

def riser(d):
    t = tt(d); f = 200 * 2 ** (3 * t / d)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5 + hp(rng.standard_normal(len(t)), 3000) * 0.4
    return (x * (t / d) ** 2).astype(np.float32)


# ---------- BGM ----------
PROG = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G
ARP = [0, 1, 2, 1, 0, 2, 1, 2]

# リズム隊を抜く区間(TOP3 発表前の「ため」)と、1位発表後の盛り上げ区間
breaks = []
for rid in ('r3', 'r2', 'r1'):
    s = SC[rid]; reveal = s['utts'][1]['start'] - 0.08
    breaks.append((s['start'] + 0.25, reveal))
climax = SC['r1']['utts'][1]['start'] - 0.08
outro_end = TOTAL - 1.8
def in_break(t): return any(a <= t < b for a, b in breaks)

drums = np.zeros(N, np.float32); bassb = np.zeros(N, np.float32); arp = np.zeros(N, np.float32)
padb = np.zeros(N, np.float32); stabs = np.zeros(N, np.float32)
KICK, CLAP = kick(), clap()
intro_drop = 1.15  # TOP10 の判子に合わせてビート開始
nb = int(np.ceil(TOTAL / BAR)) + 1
for b in range(nb):
    t0 = b * BAR
    root, chord = PROG[b % 4]
    padb_sig = pad([n + 12 for n in chord] + [chord[0]], BAR + 0.05)
    add(padb, t0, padb_sig)
    for k in range(16):
        t = t0 + k * BEAT / 4
        if t >= outro_end or in_break(t): continue
        if t < intro_drop:
            continue
        if k % 4 == 0: add(drums, t, KICK, 1.0)
        if k in (4, 12): add(drums, t, CLAP, 0.55)
        add(drums, t, hat(open_=(k % 4 == 2)), 0.22 if k % 2 else 0.12)
        if k % 2 == 1: add(bassb, t, bass(root - 12, BEAT / 2))
        if k % 2 == 0: add(arp, t, pluck(chord[ARP[(k // 2) % 8]] + 12 + (12 if t >= climax else 0)))
        if t >= climax and k in (0, 3, 6, 10):
            add(stabs, t, stab([n + 12 for n in chord]))
# 最後はトニックのコードを鳴らして終わる
add(padb, outro_end, pad([69, 72, 76, 57], 1.8) * np.linspace(1, 0, int(1.8 * SR)), 1.4)
add(drums, outro_end, KICK, 1.0); add(drums, outro_end, crash(), 0.35)

def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
music = 0.95 * norm(drums) + 0.55 * norm(bassb) + 0.32 * norm(arp) + 0.28 * norm(padb) + 0.38 * norm(stabs)
# ブレイク中はパッドだけ少し大きく(緊張感)
music = music.astype(np.float32)

# ---------- 効果音 ----------
sfx = np.zeros(N, np.float32)
add(sfx, 0.95, whoosh(0.25), 0.5); add(sfx, intro_drop, boom(), 0.9); add(sfx, intro_drop, crash(), 0.25)
WH, BM, CH = whoosh(), boom(), chime()
for rid in ('r10', 'r9', 'r8', 'r7', 'r6', 'r5', 'r4', 'r3', 'r2', 'r1'):
    s = SC[rid]; slam = s['start']
    add(sfx, slam - 0.05, WH, 0.55)
    add(sfx, slam + 0.2, BM, 0.75)
    reveal = s['utts'][1]['start'] - 0.08 if len(s['utts']) > 1 else slam + 0.12
    # 人口カウンター: 軽いティック → 完了チャイム
    for i in range(10):
        add(sfx, reveal + 0.15 + 1.0 * (1 - (1 - i / 10) ** (1 / 3)), tick(), 0.12)
    add(sfx, reveal + 1.15, CH, 0.28)
    if len(s['utts']) > 1:
        d = reveal - (slam + 0.35)
        add(sfx, slam + 0.35, drumroll(d), 0.5)
        add(sfx, slam + 0.35, riser(d), 0.18)
        add(sfx, reveal, BM, 1.0); add(sfx, reveal, crash(), 0.5)
        if rid == 'r1':
            add(sfx, reveal, CH, 0.4); add(sfx, reveal + 0.12, chime(), 0.3)

# ---------- ナレーションと合成(ダッキング) ----------
with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
hop = SR // 50
rms = np.sqrt(np.mean(np.pad(voice, (0, (-len(voice)) % hop)).reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.93)
env = np.repeat(env, hop)[:N]
speech = np.clip(env / 0.08, 0, 1)
gain = 0.5 - 0.43 * speech  # 無音時 0.50 / 発話中 0.07
gain = np.convolve(gain, np.ones(SR // 20) / (SR // 20), mode='same')
# 冒頭 0.3 秒と末尾をフェード
fade = np.ones(N, np.float32); fade[:int(0.3 * SR)] = np.linspace(0, 1, int(0.3 * SR)); fade[-int(0.8 * SR):] = np.linspace(1, 0, int(0.8 * SR))
mix = voice * 1.0 + music * gain * fade + sfx * 0.45 * (1 - 0.5 * speech) * fade
mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # 軽いソフトクリップ
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.97)

def wr(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
wr(os.path.join(OUT, 'bgm.wav'), norm(music) * 0.9)
wr(os.path.join(OUT, 'mix.wav'), mix)
print('wrote bgm.wav / mix.wav', f'{TOTAL:.2f}s')

# 動画と合成(-14 LUFS に正規化、ステレオ AAC)
mixwav = os.path.join(OUT, 'mix.wav')
m = subprocess.run(['ffmpeg', '-hide_banner', '-i', mixwav, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
      f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', mixwav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
