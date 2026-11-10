# -*- coding: utf-8 -*-
"""ナレーション(output/narration.wav)に BGM(bgm.py)をダッキングしながら重ね、無音動画と合成する。
使い方: python3 mix.py
"""
import os, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
total = len(voice) / SR
music = bgm_mod.generate(total)[:len(voice)]
with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((music * 32767).astype(np.int16).tobytes())

# ナレーションの包絡(50ms RMS、リリース約 0.5 秒)→ 発話中は BGM を下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, len(voice) - len(rms) * hop))
speech = np.clip(env / 0.1, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.16
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())

# -14 LUFS(YouTube 基準)に 2 パスで線形正規化し、ステレオ AAC で動画と合成
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
DST = os.path.join(OUT, 'chemistry_discoveries.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'video_silent.mp4'), '-i', MIX,
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
