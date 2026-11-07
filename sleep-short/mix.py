# -*- coding: utf-8 -*-
"""ナレーション + BGM(展開をタイミングに合わせる) + 効果音 をミックスし、映像と合成する。
使い方: python3 mix.py -> output/sleep_short.mp4
"""
import os, json, wave, subprocess
import numpy as np
import bgm as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = B.SR
tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
script = json.load(open(os.path.join(HERE, 'script.json'), encoding='utf-8'))
total = tl['total']; n = int(total * SR)
S = {s['id']: s for s in tl['scenes']}

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
voice = voice[:n] if len(voice) >= n else np.pad(voice, (0, n - len(voice)))

cues = {'drop': S['answer']['start'], 'bright': S['morning']['start'], 'outro': S['outro']['start']}
music = B.generate(total, cues)
music = music[:n] if len(music) >= n else np.pad(music, (0, n - len(music)))

# ---- 効果音の配置(render.html の演出と同じタイミング) ----
rng = np.random.default_rng(3)
fx = np.zeros(n, np.float32)
quiz = S['quiz']
cd0 = quiz['lines'][-1]['end'] + 0.1           # カウントダウン開始
for i in range(3):
    B.add(fx, cd0 + i * 0.62, B.sfx_tick(rng), 0.7)
B.add(fx, S['answer']['start'] - 0.35, B.sfx_whoosh(rng), 0.35)
B.add(fx, S['answer']['lines'][0]['end'] - 0.15, B.sfx_reveal(), 0.55)   # 「正解は、×」の × の瞬間
for sc in tl['scenes'][2:]:
    B.add(fx, sc['start'] - 0.2, B.sfx_whoosh(rng), 0.3)
for sid in ('bath', 'imagine', 'morning'):
    B.add(fx, S[sid]['start'] + 0.15, B.sfx_chime(), 0.35)
B.add(fx, S['morning']['lines'][0]['end'] - 0.2, B.sfx_sparkle(rng), 0.4)
B.add(fx, S['stat']['lines'][1]['start'] + 0.6, B.sfx_pop(), 0.4)
B.add(fx, S['outro']['lines'][0]['start'] + 0.2, B.sfx_pop(), 0.4)

# ---- ダッキング(発話中は BGM を下げる) ----
speech = np.zeros(n, np.float32)
for sc in tl['scenes']:
    for ln in sc['lines']:
        speech[int(ln['start'] * SR):int(ln['end'] * SR)] = 1
k = int(0.25 * SR)
speech = np.clip(np.convolve(speech, np.ones(k) / k, mode='same') * 1.5, 0, 1)
gain = 0.42 - (0.42 - 0.2) * speech
# カウントダウン中は BGM を少し上げて間を持たせる
a, b = int(cd0 * SR), int(S['answer']['start'] * SR)
gain[a:b] = 0.4
mixed = voice + music * gain + fx
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
mix_path = os.path.join(OUT, 'mix.wav')
with wave.open(mix_path, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())

# 2パスの線形 loudnorm で -14 LUFS に合わせて映像と多重化
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', mix_path, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
                    '-f', 'null', '-'], capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
af = ('loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={input_i}:measured_TP={input_tp}:'
      'measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}').format(**m)
dst = os.path.join(OUT, 'sleep_short.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'video_silent.mp4'), '-i', mix_path,
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
