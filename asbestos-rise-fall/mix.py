# -*- coding: utf-8 -*-
"""ナレーションと BGM をミックス(発話中は BGM を自動で下げる)し、映像と合成して -14 LUFS に正規化する。
使い方: python3 mix.py   → output/final.mp4
"""
import os, json, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'output'); SR = 48000
with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
music = bgm.generate()
n = len(voice); music = np.pad(music, (0, max(0, n - len(music))))[:n]
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
e = np.zeros_like(rms)
for i, v in enumerate(rms): e[i] = max(v, (e[i - 1] if i else 0.0) * 0.9)
e = np.pad(np.repeat(e, hop), (0, n - len(e) * hop))
speech = np.clip(e / 0.10, 0, 1)
gain = 0.50 - (0.50 - 0.20) * speech                 # 無音時 0.50 / 発話時 0.20
k = SR // 8; gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
with wave.open(os.path.join(OUT, 'mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mixed * 32767).astype(np.int16).tobytes())
src, mixw, dst = (os.path.join(OUT, f) for f in ('video_silent.mp4', 'mix.wav', 'final.mp4'))
m = subprocess.run(['ffmpeg', '-hide_banner', '-i', mixw, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
      f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
if os.path.exists(src):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', mixw, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af,
                    '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
    print('wrote', dst)
