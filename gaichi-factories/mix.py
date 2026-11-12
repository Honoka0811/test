# -*- coding: utf-8 -*-
"""ナレーションと BGM(bgm.py)をミックスし、無音動画に合成して完成版を書き出す。
BGM はナレーション中だけ自動で音量を下げる(ダッキング)。音量は -14 LUFS に正規化。
使い方: python3 mix.py   (先に narrate.py と capture.js を実行しておく)
"""
import os, re, json, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
O = lambda f: os.path.join(HERE, 'output', f)
SR = 48000
with wave.open(O('narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
music = bgm.generate(len(voice) / SR)[:len(voice)]
music = np.pad(music, (0, len(voice) - len(music)))

hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.93)                 # リリース約0.7秒
env = np.pad(np.repeat(env, hop), (0, len(voice) - len(rms) * hop))
speech = np.clip(env / 0.08, 0, 1)
gain = 0.50 - (0.50 - 0.17) * speech                                   # 無音時 / 発話時の BGM ゲイン
k = SR // 8
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
mixed /= max(1.0, np.max(np.abs(mixed)) / 0.95)

def save(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
save(O('bgm.wav'), music); save(O('mix.wav'), mixed)

LN = 'loudnorm=I=-14:TP=-1.5:LRA=11'
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', O('mix.wav'), '-af', LN + ':print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True)
m = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr).group(0))
af = (f"{LN}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
dst = O('gaichi_factories_short.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', O('video_silent.mp4'), '-i', O('mix.wav'),
                '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
