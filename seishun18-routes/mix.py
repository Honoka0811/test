# -*- coding: utf-8 -*-
"""ナレーション(output/narration.wav)に BGM をダッキングしながらミックスし、無音の映像と合成する。
使い方: python3 mix.py   → output/seishun18_routes.mp4
"""
import os, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000

with open(os.path.join(HERE, 'timing.js'), encoding='utf-8') as f:
    TOTAL = json.loads(f.read().split('=', 1)[1].strip().rstrip(';'))['total']

with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
music = bgm_mod.generate(TOTAL)
n = min(len(voice), len(music)); voice, music = voice[:n], music[:n]
with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((music * 32767).astype(np.int16).tobytes())

# ダッキング: 50ms RMS の包絡 → リリース 0.5 秒
hop = SR // 20
rms = np.sqrt(np.mean(np.pad(voice, (0, -n % hop)).reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0) * 0.9)
envl = np.repeat(envl, hop)[:n]
speech = np.clip(envl / 0.1, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.38, 0.15
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())

SRC = os.path.join(OUT, 'video_silent.mp4')
DST = os.path.join(OUT, 'seishun18_routes.mp4')
# 2パス: 積分ラウドネスを測って -14 LUFS(YouTube 基準)へ線形ゲイン
import re
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])
print(f'mix loudness {I:.1f} LUFS -> gain {-14 - I:+.1f} dB')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX, '-c:v', 'copy',
                '-af', f'volume={-14 - I:.2f}dB,alimiter=limit=0.84:level=false', '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
