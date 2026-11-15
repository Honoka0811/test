# -*- coding: utf-8 -*-
"""ナレーション + BGM(ナレーション中は自動で音量を下げる)をミックスし、
無音動画と合成して -14 LUFS に正規化した最終 mp4 を書き出す。"""
import os, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
O = lambda f: os.path.join(HERE, 'output', f)
SR = 48000
total = json.load(open(O('timeline.json')))['total']

with wave.open(O('narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
n = len(voice)
music = bgm_mod.generate(total)[:n]
music = np.pad(music, (0, n - len(music)))

# ダッキング: 50ms RMS 包絡 → 速いアタック / 0.4 秒リリース
hop = SR // 20
rms = np.sqrt(np.mean(np.pad(voice, (0, -n % hop)).reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.88)
env = np.repeat(env, hop)[:n]
gain = 0.30 - (0.30 - 0.06) * np.clip(env / 0.1, 0, 1)
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
mixed = voice + music * gain
mixed /= max(1.0, np.max(np.abs(mixed)) / 0.95)
with wave.open(O('mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())

# -14 LUFS(2 パス loudnorm, linear)でステレオ AAC に
meas = subprocess.run(['ffmpeg', '-hide_banner', '-i', O('mix.wav'), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
                       '-f', 'null', '-'], capture_output=True, text=True).stderr
m = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
dst = O('todai_sugoi_10.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', O('video_silent.mp4'), '-i', O('mix.wav'), '-c:v', 'copy',
                '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
