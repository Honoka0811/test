# -*- coding: utf-8 -*-
"""ナレーション + BGM(G線上のアリア)をダッキングしながらミックスし、映像と合成する。
前提: narrate.py(output/narration.wav, timeline.js)と capture.js(output/pacific_war_battles.mp4)を実行済み。
"""
import os, wave, json, subprocess
import numpy as np
import bgm_air

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
TL = json.loads(open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read().split('=', 1)[1].rstrip().rstrip(';'))
TOTAL = TL['total']

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
music = bgm_air.generate(TOTAL)
bgm_air.write_wav(os.path.join(OUT, 'bgm.wav'), music)
n = min(len(voice), len(music)); voice = voice[:n]; music = music[:n]

# ナレーションの包絡(50ms RMS、リリース約0.6秒)→ BGM のゲイン
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.92)
env = np.pad(np.repeat(env, hop), (0, n - n // hop * hop), mode='edge')
speech = np.clip(env / 0.10, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.50, 0.20
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 8
gain = np.convolve(np.pad(gain, (k, k), mode='edge'), np.ones(k) / k, mode='same')[k:-k]
mix = music * gain[:, None] + voice[:, None]
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
wav = os.path.join(OUT, 'mix.wav')
with wave.open(wav, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
dst = os.path.join(OUT, 'pacific_war_battles_narrated.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'pacific_war_battles.mp4'), '-i', wav,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
