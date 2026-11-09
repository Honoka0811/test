# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング)をミックスし、無音動画と合成して -14 LUFS に正規化した最終 mp4 を書き出す。"""
import os, wave, json, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
total = len(voice) / SR
music = bgm_mod.generate(total)[:len(voice)]
music = np.pad(music, (0, len(voice) - len(music)))
with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((music * 32767).astype(np.int16).tobytes())

# ダッキング: 発話中は BGM を下げる(アタック速め・リリース約 0.4 秒)
hop = SR // 50
n = len(voice) // hop * hop
rms = np.sqrt(np.mean(voice[:n].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.95)
env = np.pad(np.repeat(env, hop), (0, len(voice) - n))
speech = np.clip(env / 0.08, 0, 1)
gain = 0.30 - (0.30 - 0.13) * speech           # 無音時 / 発話時の BGM ゲイン
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mix = voice + music * gain
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())

# -14 LUFS(YouTube 基準)へ 2 パス正規化し、ステレオ AAC で多重化
m = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
      f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
DST = os.path.join(OUT, 'shikaku_short.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'video_silent.mp4'), '-i', MIX, '-map', '0:v', '-map', '1:a',
                '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
