# -*- coding: utf-8 -*-
"""ナレーション + BGM(ナレーション中は自動で音量を下げる)をミックスし、映像と合成して
-14 LUFS に正規化した最終 mp4 を書き出す。使い方: python3 mix.py"""
import os, wave, subprocess, json
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
VIDEO = os.path.join(OUT, 'video_silent.mp4')
FINAL = os.path.join(OUT, 'kyushu_univ_top10.mp4')

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
total = json.loads(open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read().split('=', 1)[1].rstrip().rstrip(';'))['total']
n = int(total * SR)
voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]
music = bgm.generate(total)[:n]
music = np.pad(music, ((0, n - len(music)), (0, 0)))

# ダッキング:ナレーションの包絡(50ms RMS、リリース約0.4秒)で BGM ゲインを下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0) * 0.88)
envl = np.pad(np.repeat(envl, hop), (0, n - len(rms) * hop))
speech = np.clip(envl / 0.10, 0, 1)
gain = 0.55 - (0.55 - 0.22) * speech
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
mixed = music * gain[:, None] + voice[:, None]
mixed /= max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())

# 2 パス loudnorm で -14 LUFS(ショート動画プラットフォームの基準)に正規化
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
                    '-f', 'null', '-'], capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', VIDEO, '-i', MIX, '-map', '0:v', '-map', '1:a',
                '-c:v', 'copy', '-af', af, '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                '-movflags', '+faststart', FINAL], check=True)
print('wrote', FINAL)
