# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング)をミックスし、無音動画と合成して最終 mp4 を書き出す。
使い方: python3 mix.py   (先に tts.py → node capture.js を実行しておく)
"""
import os, json, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
total = json.load(open(os.path.join(OUT, 'timeline.json')))['total']

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
n = int(total * SR)
voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]
music = bgm.generate(total)[:n]
music = np.pad(music, (0, n - len(music)))

# ダッキング: ナレーションの包絡(50ms RMS, リリース約0.4秒)で BGM を下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.88)
env = np.pad(np.repeat(env, hop), (0, n - n // hop * hop))
speech = np.clip(env / 0.1, 0, 1)
gain = 0.42 - (0.42 - 0.20) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mix = voice + music * gain
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
with wave.open(os.path.join(OUT, 'mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((music * 32767).astype(np.int16).tobytes())

# -14 LUFS(ショート動画向け)に2パス正規化してステレオ AAC で多重化
src = os.path.join(OUT, 'mix.wav')
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', src, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
dst = os.path.join(OUT, 'hokudai_sugoi_top10.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'video_silent.mp4'), '-i', src,
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
