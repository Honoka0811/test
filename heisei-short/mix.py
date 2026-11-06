# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング) + 効果音 をミックスし、映像と合わせて -14 LUFS で書き出す。
使い方: python3 mix.py   (先に narrate.py と capture.js を実行しておく)
"""
import os, json, re, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); UP = os.path.join(HERE, 'upload'); os.makedirs(UP, exist_ok=True)
SR = bgm.SR
js = open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read()
TL = json.loads(re.search(r'TIMELINE = (\[.*?\]);', js, re.S).group(1))
TOTAL = float(re.search(r'DURATION = ([\d.]+)', js).group(1))
S = {s['id']: s for s in TL}
N = int(TOTAL * SR)
rng = np.random.default_rng(11)

def read(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
def fit(x): return x[:N] if len(x) >= N else np.pad(x, (0, N - len(x)))
voice = fit(read(os.path.join(OUT, 'narration.wav')))

# ---------- 効果音(すべて合成) ----------
def tone(f, dur, decay, kind='sin'):
    t = np.arange(int(dur * SR)) / SR
    w = np.sin(2 * np.pi * f * t) if kind == 'sin' else np.sign(np.sin(2 * np.pi * f * t)) * 0.5
    return (w * np.exp(-t / decay)).astype(np.float32)
def whoosh(dur=0.35):
    n = int(dur * SR); x = rng.standard_normal(n).astype(np.float32)
    k = np.linspace(40, 4, n).astype(int); y = np.empty_like(x); c = np.cumsum(np.insert(x, 0, 0))
    idx = np.arange(n); lo = np.maximum(0, idx - k); y = (c[idx + 1] - c[lo]) / (idx + 1 - lo)
    return (y * np.sin(np.linspace(0, np.pi, n)) ** 2 * 3).astype(np.float32)
def ding():  # カウンター加算「ピコン」
    return np.concatenate([tone(1318, 0.07, 0.05, 'sq'), tone(1976, 0.25, 0.08, 'sq')]) * 0.6
def scratch():  # レコードスクラッチ
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 300 + 900 * np.abs(np.sin(2 * np.pi * 3.5 * t)); x = rng.standard_normal(n) * 0.4 + np.sin(2 * np.pi * np.cumsum(f) / SR)
    x = np.convolve(x, np.ones(5) / 5, 'same'); return (x * np.exp(-t / 0.25) * 0.8).astype(np.float32)
def buzz(dur=0.85):  # ポケベルのバイブ
    t = np.arange(int(dur * SR)) / SR
    return (np.sign(np.sin(2 * np.pi * 70 * t)) * 0.3 * (np.sin(2 * np.pi * 7 * t) > 0)).astype(np.float32)
def beep():  # 赤外線「ピッ」
    return tone(2800, 0.18, 0.2, 'sq') * 0.5
def pop_():
    return tone(600, 0.15, 0.03) + tone(1200, 0.15, 0.02) * 0.5
def chime():  # エンディング「ジャーン」
    return sum(tone(bgm.hz(m), 1.6, 0.6) for m in (72, 76, 79, 84)) * 0.35

sfx = np.zeros(N + SR, np.float32)
for s in TL:
    if s['id'] not in ('hook', 'safe'):
        bgm.add(sfx, max(0, s['start'] - 0.15), whoosh(), 0.35)
    if s['id'] in ('cd', 'pager', 'puri', 'socks', 'nostra', 'bill', 'melody', 'ir'):
        bgm.add(sfx, s['start'] + 0.05, ding(), 0.45)
bgm.add(sfx, 0.0, pop_(), 0.6)
bgm.add(sfx, 1.35, pop_(), 0.5)
bgm.add(sfx, S['pager']['start'], buzz(), 0.35)
bgm.add(sfx, S['safe']['start'], scratch(), 0.55)
bgm.add(sfx, S['safe']['start'] + 0.3, pop_(), 0.6)
bgm.add(sfx, S['ir']['vend'] - 0.45, beep(), 0.6)
bgm.add(sfx, S['end']['start'] + 1.6, chime(), 0.5)
for i in range(8): bgm.add(sfx, S['end']['start'] + 0.1 + i * 0.12, tone(1500 + i * 120, 0.08, 0.04, 'sq'), 0.15)
sfx = sfx[:N]

# ---------- BGM(ノストラダムス場面は不穏に) + ダッキング ----------
music = fit(bgm.generate(TOTAL, tension=(S['nostra']['start'], S['safe']['start'] + 0.35)))
hop = SR // 50
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
e = np.zeros_like(rms)
for i, v in enumerate(rms): e[i] = max(v, (e[i - 1] if i else 0) * 0.93)
e = np.pad(np.repeat(e, hop), (0, N - len(rms) * hop))
gain = 0.40 - (0.40 - 0.12) * np.clip(e / 0.08, 0, 1)
gain = np.convolve(gain, np.ones(SR // 20) / (SR // 20), 'same')
mix = voice * 1.0 + music * gain + sfx * 0.8
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.95)

def wr(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
wr(os.path.join(OUT, 'bgm.wav'), music)
wr(os.path.join(OUT, 'mix.wav'), mix)

# ---------- 映像と合成 → -14 LUFS(2パス) ----------
silent = os.path.join(OUT, 'video_silent.mp4'); tmp = os.path.join(OUT, 'heisei_mix.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', os.path.join(OUT, 'mix.wav'),
                '-c:v', 'copy', '-c:a', 'pcm_s16le', '-shortest', os.path.join(OUT, 'tmp.mov')], check=True)
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', os.path.join(OUT, 'tmp.mov'), '-af',
                    'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
m = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
final = os.path.join(UP, 'heisei_aruaru_short.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'tmp.mov'), '-c:v', 'copy', '-af', af,
                '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', final], check=True)
os.remove(os.path.join(OUT, 'tmp.mov'))
subprocess.run(['cp', os.path.join(OUT, 'subtitles_ja.srt'), UP])
print('wrote', final)
