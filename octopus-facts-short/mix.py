# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング) + 効果音をミックスし、映像と合成して最終 mp4 を書き出す。
使い方: python3 mix.py   (先に narrate.py と node capture.js を実行しておく)
"""
import os, json, wave, subprocess
import numpy as np
import bgm as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = B.SR
tl = json.load(open(os.path.join(OUT, 'timeline.json')))
TOTAL = tl['total']
S = {s['name']: s for s in tl['scenes']}
C = {n: [c[0] for c in s['cues']] for n, s in S.items()}   # 各キューの絶対時刻

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
N = int(TOTAL * SR)
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]

# ---------- BGM ----------
blind_t = C['color'][3] + 0.35
music = B.generate(TOTAL, drop_at=S['color']['start'], quiet=[(blind_t, blind_t + 1.0)])
music = np.pad(music, (0, max(0, N - len(music))))[:N]

# ---------- SFX (render.html の演出タイミングに合わせる) ----------
sfx = np.zeros(N + SR, dtype=np.float32)
add = lambda x, t, g=1.0: B.add(sfx, x.astype(np.float32), t, g)
add(B.boom(), 0.0, 0.8)
add(B.glitch(), 0.0, 0.35)
for i, sc in enumerate(tl['scenes'][1:], 1):
    add(B.whoosh(), sc['start'] - 0.3, 0.55)
    if sc['name'] != 'outro':
        add(B.boom(), sc['start'] + 0.02, 0.9 if sc['name'] == 'color' else 0.7)
# hook
add(B.pop(), C['hook'][1] + 0.55, 1.0); add(B.boom(), C['hook'][1] + 0.55, 0.35)
add(B.chime(), C['hook'][2] + 0.6, 0.7)
# hearts: 主心臓の鼓動(描画の beat() と同期)→停止でフラットライン
hs = S['hearts']['start']; stop = C['hearts'][2] + 0.9
lt = C['hearts'][1] + 0.2 - hs
while hs + lt < stop:
    if ((lt + 0.12) % 0.8) < 1 / 30:
        add(B.heartbeat(), hs + lt, 0.9)
    lt += 1 / 30
add(B.flatline(), stop, 1.0)
# blood
add(B.chime(1046.5), C['blood'][1] + 0.45, 0.7)
add(B.pop(), C['blood'][2], 0.9)
add(B.glitch()[:SR // 6], C['blood'][3] + 0.35, 0.6)
# brains
add(B.chime(1568), C['brains'][2], 0.5)
for k in range(8):
    add(B.pop(), C['brains'][3] + 0.1 + k * 0.17, 0.8)
# taste
for i in range(4):
    add(B.pop(), C['taste'][1] + 0.5 + i * 0.25, 0.8)
add(B.chime(1760), C['taste'][3], 0.5)
# color
add(B.glitch(), blind_t, 0.9); add(B.boom(), blind_t, 0.6)
# outro
for i in range(5):
    add(B.pop(), S['outro']['start'] + 0.3 + i * 0.12, 0.6)
add(B.pop(), C['outro'][1], 1.0)
add(B.whoosh(0.6), C['outro'][2] + 0.1, 0.5)
sfx = sfx[:N]

# ---------- ダッキング ----------
hop = SR // 50
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
e = np.zeros_like(rms)
for i, v in enumerate(rms):
    e[i] = max(v, (e[i - 1] if i else 0) * 0.93)
duck = 1 - 0.62 * np.clip(e / 0.05, 0, 1)
duck = np.interp(np.arange(N), np.arange(len(duck)) * hop, duck)

mixd = voice * 1.0 + music * 0.42 * duck + sfx * 0.55
mixd = np.tanh(mixd * 0.95)
with wave.open(os.path.join(OUT, 'mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixd * 32767).astype(np.int16).tobytes())
with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((music * 32767).astype(np.int16).tobytes())
print('wrote mix.wav / bgm.wav')

# ---------- 映像と合成 + -14 LUFS 正規化(YouTube 基準) ----------
src = os.path.join(OUT, 'octopus_video.mp4')
up = os.path.join(HERE, 'upload'); os.makedirs(up, exist_ok=True)
dst = os.path.join(up, 'octopus_facts_short.mp4')
mixwav = os.path.join(OUT, 'mix.wav')
meas = subprocess.run(['ffmpeg', '-hide_banner', '-i', mixwav, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                      capture_output=True, text=True).stderr
m = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', src, '-i', mixwav, '-map', '0:v', '-map', '1:a',
                '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
