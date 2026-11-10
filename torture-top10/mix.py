# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング)をミックスし、無音動画と合成して最終mp4を書き出す(-14 LUFS / ステレオAAC)。"""
import os, json, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'output'); SR = 48000
TL = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
hits = [s['start'] for s in TL['scenes'] if s['kind'] == 'item']
music = bgm.generate(TL['total'], hits)[:len(voice)]
music = np.pad(music, (0, len(voice) - len(music)))
with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((music * 32767).astype(np.int16).tobytes())

hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, len(voice) - len(rms) * hop))
gain = 0.42 - (0.42 - 0.17) * np.clip(env / 0.1, 0, 1)
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), 'same')
mix = voice + music * gain
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())

DST = os.path.join(OUT, 'worst_torture_top10.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'video_silent.mp4'), '-i', MIX,
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ac', '2', '-ar', '48000',
    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
