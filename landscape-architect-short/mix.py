# -*- coding: utf-8 -*-
"""ナレーションに BGM をダッキングしながら重ね、-14 LUFS に正規化して無音動画に合成する。
使い方: python3 mix.py   (事前に narrate.py と capture.js を実行しておく)"""
import os, json, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
O = lambda *p: os.path.join(HERE, 'output', *p)
SR = 48000
with wave.open(O('narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
music = bgm.generate(len(voice) / SR)
music = np.pad(music, (0, max(0, len(voice) - len(music))))[:len(voice)]

# ナレーションの包絡(50ms RMS、リリース約0.5秒)に応じて BGM を下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, env[i - 1] * 0.9 if i else 0)
env = np.pad(np.repeat(env, hop), (0, len(voice) - len(rms) * hop))
speech = np.clip(env / 0.1, 0, 1)
gain = 0.42 - (0.42 - 0.13) * speech          # 無音時 / 発話時の BGM ゲイン
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
mixed /= max(1.0, np.max(np.abs(mixed)) / 0.95)
with wave.open(O('mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())
with wave.open(O('bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((music * 32767).astype(np.int16).tobytes())

# 2パス loudnorm(線形)で -14 LUFS に
ln = 'loudnorm=I=-14:TP=-1.5:LRA=11'
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', O('mix.wav'), '-af', ln + ':print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
af = (f"{ln}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
dst = O('landscape_architect_short.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', O('video_silent.mp4'), '-i', O('mix.wav'),
                '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
