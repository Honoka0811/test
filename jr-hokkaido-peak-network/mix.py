# -*- coding: utf-8 -*-
"""ナレーション(narration.wav)と BGM(bgm.wav)をダッキングしながらミックスし、
無音の映像と合わせて最終 mp4 を作る。音量は -14 LUFS(YouTube 基準)に正規化。
使い方: python3 mix.py
"""
import os, wave, json, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000

def read(p):
    with wave.open(p) as w:
        assert w.getframerate() == SR
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768

voice = read(os.path.join(OUT, 'narration.wav'))
music = read(os.path.join(OUT, 'bgm.wav'))
n = max(len(voice), len(music))
voice = np.pad(voice, (0, n - len(voice))); music = np.pad(music, (0, n - len(music)))

# ナレーションの包絡(50ms RMS、アタック速め・リリース約0.4秒)→ BGM を沈める
hop = SR // 20
rms = np.sqrt(np.mean(np.pad(voice, (0, (-n) % hop)).reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0) * 0.88)
envl = np.repeat(envl, hop)[:n]
speech = np.clip(envl / 0.08, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.16
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mix = voice * 1.0 + music * gain
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.97)

MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print('wrote', MIX)

SRC = os.path.join(OUT, 'video_silent.mp4')
DST = os.path.join(OUT, 'jr_hokkaido_peak_network.mp4')
# 2パス loudnorm(1パス目で計測 → 2パス目で線形ゲイン調整)
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
