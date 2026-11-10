# -*- coding: utf-8 -*-
"""BGM(bgm.py)をナレーション中だけ自動で下げて(ダッキング)ミックスし、無音動画と合成して -14 LUFS に正規化する。
使い方: python3 mix.py  → output/physics_discoveries.mp4
"""
import os, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
total = json.load(open(os.path.join(OUT, 'timings.json')))['total']

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
music = bgm_mod.generate(total)
n = max(len(voice), len(music))
voice = np.pad(voice, (0, n - len(voice))); music = np.pad(music, (0, n - len(music)))

# ナレーションの包絡 → BGM ゲイン(発話時は下げる)
hop = SR // 20
rms = np.sqrt(np.mean(np.pad(voice, (0, -len(voice) % hop)).reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
env = np.repeat(env, hop)[:n]
speech = np.clip(env / 0.1, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.17
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
mix = voice + music * gain
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

# 2 パス loudnorm で -14 LUFS(YouTube 基準)に揃え、ステレオ AAC で多重化
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
DST = os.path.join(OUT, 'physics_discoveries.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'video_silent.mp4'), '-i', MIX,
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
