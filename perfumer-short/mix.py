# -*- coding: utf-8 -*-
"""ナレーションと BGM をミックスし(発話中は BGM を自動で下げる=ダッキング)、無音動画に合成する。
使い方: python3 mix.py [無音mp4] [出力mp4]
"""
import sys, os, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'perfumer_short.mp4')
SR = 48000

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
total = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))['total']
music = bgm_mod.generate(total)
n = len(voice)
music = music[:n] if len(music) >= n else np.pad(music, (0, n - len(music)))

# ナレーションの包絡(50ms RMS, リリース約0.5秒) → BGM ゲイン
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
speech = np.clip(env / 0.1, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.16
gain = np.convolve(BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech, np.ones(SR // 10) / (SR // 10), mode='same')
mixed = voice + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)

with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((music * 32767).astype(np.int16).tobytes())
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mixed * 32767).astype(np.int16).tobytes())

# 2パス loudnorm で -14 LUFS(YouTube 基準)に正規化し、ステレオ AAC で多重化
meas = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                      capture_output=True, text=True).stderr
m = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
