# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング) + 効果音をミックスし、映像と合成して最終 mp4 を書き出す。
使い方: python3 mix.py   (先に tts.py → node capture.js を実行しておく)
出力: output/mix.wav, output/manchukuo_cities_final.mp4 (-14 LUFS / ステレオ AAC)
"""
import os, json, wave, subprocess
import numpy as np
import music

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = music.SR
VIDEO = os.path.join(OUT, 'manchukuo_cities.mp4')
FINAL = os.path.join(OUT, 'manchukuo_cities_final.mp4')

def read(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

timing = music.load_timing()
nar = read(os.path.join(OUT, 'narration.wav'))
bgm, sfx = music.generate(timing)
n = len(nar)
fit = lambda x: x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))
bgm, sfx = fit(bgm), fit(sfx)

# ダッキング: ナレーションの包絡(50ms RMS、リリース約0.5秒)で BGM を下げる
hop = SR // 20
rms = np.sqrt(np.mean(nar[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, n - len(env) * hop))
speech = np.clip(env / 0.10, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.55, 0.26
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = nar * 1.0 + bgm * gain + sfx * 0.45
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())
print('wrote', MIX)

# -14 LUFS(YouTube 基準)に 2 パスで正規化してステレオ AAC で多重化
meas = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                      capture_output=True, text=True).stderr
j = json.loads(meas[meas.rindex('{'): meas.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
      f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', VIDEO, '-i', MIX, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', FINAL], check=True)
print('wrote', FINAL)
