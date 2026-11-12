# -*- coding: utf-8 -*-
"""ナレーションと BGM をミックスして動画に合成する。
BGM はナレーション中に自動で音量を下げる(ダッキング)。最終音量は -14 LUFS に正規化。
使い方: python3 mix.py [無音mp4] [出力mp4]
"""
import os, re, sys, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'furniture_craftsman_short.mp4')
SR = 48000
BGM_SILENT, BGM_SPEECH = 0.50, 0.17      # 無音時 / 発話時の BGM ゲイン(線形)

timing = json.loads(re.search(r'=\s*(\{.*\})\s*;', open(os.path.join(OUT, 'timing.js'), encoding='utf-8').read(), re.S).group(1))
total = timing['total']

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
n = int(total * SR)
voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]

music = bgm_mod.generate(total)[:n]
with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((music * 32767).astype(np.int16).tobytes())

# ナレーションの包絡(50ms RMS → リリース約0.5秒)からダッキング量を決める
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
speech = np.clip(env / 0.10, 0, 1)
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 8
gain = np.convolve(np.pad(gain, k, mode='edge'), np.ones(k) / k, mode='same')[k:-k]

mixed = music * gain[:, None] + voice[:, None] * 0.9
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX,
                '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
