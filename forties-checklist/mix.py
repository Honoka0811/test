# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング) + 効果音をミックスし、無音の動画に合成する。
使い方: python3 mix.py [入力mp4] [出力mp4]
  入力既定: output/forties_checklist.mp4(capture.js の出力)
  出力既定: output/forties_checklist_narrated.mp4
前提: output/narration.wav と output/timing.json(narrate.py の出力)。BGM は bgm.py でその場で合成する。
効果音(シーン切替のポップ音・まとめのチェック音)は numpy で合成(外部素材なし)。
"""
import os, sys, json, wave, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'forties_checklist.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'forties_checklist_narrated.mp4')
SR = 48000

timing = json.load(open(os.path.join(OUT, 'timing.json'), encoding='utf-8'))
TOTAL = timing['total']
N = int(TOTAL * SR)

def read_wav(path):
    with wave.open(path) as w:
        ch, sr = w.getnchannels(), w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    assert sr == SR, (path, sr)
    return x.reshape(-1, ch)

def fit(x, n):
    return x[:n] if len(x) >= n else np.pad(x, ((0, n - len(x)), (0, 0)))

# ---------- ナレーション(モノラル → 中央) ----------
narr = fit(read_wav(os.path.join(OUT, 'narration.wav')), N)[:, 0]

# ---------- BGM ----------
sys.path.insert(0, HERE)
import bgm as bgm_mod
bgm_path = os.path.join(OUT, 'bgm.wav')
music = bgm_mod.generate(TOTAL)
bgm_mod.write_wav(bgm_path, music)
music = fit(music, N)

# ナレーションの包絡でダッキング(アタック速く・リリース約0.6秒)
hop = SR // 20
rms = np.sqrt(np.mean(narr[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.92)
env = np.pad(np.repeat(env, hop), (0, N - len(rms) * hop))
speech = np.clip(env / 0.10, 0, 1)
BGM_FREE, BGM_DUCK = 0.42, 0.17          # 無音時 / 発話時の BGM ゲイン(線形)
gain = BGM_FREE - (BGM_FREE - BGM_DUCK) * speech
k = SR // 8
gain = np.convolve(gain, np.ones(k) / k, mode='same')

# ---------- 効果音 ----------
def add(buf, t, sig, pan=0.0):
    s = int(t * SR); e = min(s + len(sig), N)
    if e <= s: return
    l, r = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    buf[s:e, 0] += sig[:e - s] * l; buf[s:e, 1] += sig[:e - s] * r

def pop(f0=900, f1=300, dur=0.14, amp=0.22):
    """シーン切替の「ポンッ」(下降サイン + 短いノイズ)"""
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.045)
    return (sig * amp).astype(np.float32)

def whoosh(dur=0.35, amp=0.10, seed=1):
    """ワイプの「シュッ」(帯域ノイズのスウィープ)"""
    rs = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rs.standard_normal(n).astype(np.float32)
    # 簡易ローパス(移動平均)を時間で狭める → 上昇感
    out = np.zeros(n, dtype=np.float32)
    win = 64
    sm = np.convolve(noise, np.ones(win) / win, mode='same')
    out = (noise - sm) * np.sin(np.pi * t / dur) ** 1.5
    return (out / (np.max(np.abs(out)) or 1) * amp).astype(np.float32)

def ding(freq=1318.5, dur=0.5, amp=0.16):
    """チェック音(倍音つきのベル)"""
    t = np.arange(int(dur * SR)) / SR
    sig = (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t / 0.08)) * np.exp(-t / 0.14)
    return (sig * amp).astype(np.float32)

def sparkle(dur=0.6, amp=0.12):
    """タイトルの「キラッ」(上昇アルペジオ)"""
    out = np.zeros(int(dur * SR), dtype=np.float32)
    for i, f in enumerate([1046.5, 1318.5, 1568, 2093]):
        t = np.arange(int(0.35 * SR)) / SR
        s = int(i * 0.06 * SR)
        sig = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.12) * amp
        out[s:s + len(sig)] += sig[:len(out) - s]
    return out

sfx = np.zeros((N, 2), dtype=np.float32)
for sc in timing['scenes']:
    if sc['id'] == 'intro':
        add(sfx, sc['start'] + 0.05, pop(700, 250, amp=0.2)); add(sfx, sc['start'] + 0.3, pop(800, 300, amp=0.18))
        add(sfx, sc['start'] + 0.62, sparkle())
    elif sc['id'] == 'outro':
        add(sfx, sc['start'], whoosh(seed=99))
        for i in range(10):
            add(sfx, sc['start'] + 0.35 + i * 0.17 + 0.12, ding(1318.5 * (2 ** (min(i, 7) / 12)), amp=0.11), pan=-0.3 + 0.06 * i)
        add(sfx, sc['start'] + 2.65, sparkle(amp=0.14))
    else:
        add(sfx, sc['start'], whoosh(seed=int(sc['start'] * 10)))           # 円形ワイプ
        add(sfx, sc['start'] + 0.08, pop(amp=0.22), pan=-0.4)                # 番号バッジ
        add(sfx, sc['start'] + 0.78, pop(1100, 500, dur=0.09, amp=0.12), pan=0.2)   # サブのピル

# ---------- ミックス ----------
mixed = np.zeros((N, 2), dtype=np.float32)
mixed[:, 0] += narr; mixed[:, 1] += narr
mixed += music * gain[:, None]
mixed += sfx
mixed /= max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())
print('wrote', MIX, f'({TOTAL}s)')

if os.path.exists(SRC):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX,
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
    print('wrote', DST)
else:
    print('動画が無いので音声ミックスのみ書き出しました:', SRC)
