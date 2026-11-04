# -*- coding: utf-8 -*-
"""ナレーション + BGM(発話中は自動で下げる) + 効果音 をミックスし、無音の映像と合成する。
使い方: python3 mix.py [映像mp4] [出力mp4]
"""
import os, sys, wave, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'leather_shoes_top10.mp4')
SR = 48000

def read(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

voice, music, sfx = (read(os.path.join(OUT, f)) for f in ('narration.wav', 'bgm.wav', 'sfx.wav'))
n = len(voice)
fit = lambda x: x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))
music, sfx = fit(music), fit(sfx)

# ダッキング: ナレーションの包絡(50ms RMS、リリース約0.4秒)で BGM を下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.88)
env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
speech = np.clip(env / 0.1, 0, 1)
gain = 0.55 - (0.55 - 0.24) * speech        # 無音時 / 発話時
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mix = voice * 1.0 + music * gain + sfx * 0.5
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.95)
wav = os.path.join(OUT, 'mix.wav')
with wave.open(wav, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

# -14 LUFS に正規化してステレオ AAC で合成
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', wav, '-c:v', 'copy',
                '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
