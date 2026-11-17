# -*- coding: utf-8 -*-
"""ナレーション(output/narration.wav)に BGM(bgm.py)をダッキングしながら重ね、無音の映像と合成して完成動画を書き出す。
音量は -14 LUFS(YouTube 基準)に正規化する。
使い方: python3 mix.py   →  output/kyugun_sugoi_short.mp4
"""
import os, json, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
tl = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
music = bgm.generate(len(voice) / SR, hits=[s['start'] for s in tl['scenes']])[:len(voice)]
with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((music * 32767).astype(np.int16).tobytes())

# ナレーションの包絡(50ms RMS、リリース約0.5秒)から BGM のゲインを決める
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, len(voice) - len(env) * hop))
speech = np.clip(env / 0.08, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.15      # 無音時 / 発話時の BGM ゲイン
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10; gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
mixed /= max(1.0, np.max(np.abs(mixed)) / 0.95)
mix_wav = os.path.join(OUT, 'mix.wav')
with wave.open(mix_wav, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mixed * 32767).astype(np.int16).tobytes())

src = os.path.join(OUT, 'video_silent.mp4'); dst = os.path.join(OUT, 'kyugun_sugoi_short.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', mix_wav, '-c:v', 'copy',
                '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', dst], check=True)
os.remove(mix_wav)
print('wrote', dst)
