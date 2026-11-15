# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング)をミックスし、無音動画と合成して -14 LUFS に正規化した最終mp4を作る。"""
import os, wave, json, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'output')
SR = 48000
with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
music = bgm.generate(len(voice) / SR)
music = np.pad(music, (0, max(0, len(voice) - len(music))))[:len(voice)]
# ナレーションの包絡でBGMを下げる
hop = SR // 20
rms = np.sqrt(np.mean(np.pad(voice, (0, -len(voice) % hop)).reshape(-1, hop) ** 2, axis=1))
e = np.zeros_like(rms)
for i, v in enumerate(rms):
    e[i] = max(v, (e[i - 1] if i else 0) * 0.9)
e = np.repeat(e, hop)[:len(voice)]
gain = 0.42 - (0.42 - 0.17) * np.clip(e / 0.1, 0, 1)
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
mix = voice + music * gain
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
with wave.open(os.path.join(OUT, 'mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

src, dst = os.path.join(OUT, 'video_silent.mp4'), os.path.join(OUT, 'nagoya_univ_top10.mp4')
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', os.path.join(OUT, 'mix.wav'), '-af',
                    'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
m = json.loads(r.stderr[r.stderr.rindex('{'):])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', os.path.join(OUT, 'mix.wav'),
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
