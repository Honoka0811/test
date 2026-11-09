# -*- coding: utf-8 -*-
"""ナレーション(output/narration.wav)に BGM(bgm.py)をダッキングしながら重ね、映像と合成する。
使い方: python3 mix.py [入力mp4(無音)] [出力mp4]
"""
import sys, os, wave
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'frenemy_video.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'frenemy_narrated.mp4')
SR = bgm_mod.SR

with wave.open(os.path.join(HERE, 'output', 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
total = len(voice) / SR
music = bgm_mod.generate(total)
music = np.pad(music, (0, max(0, len(voice) - len(music))))[:len(voice)]
with wave.open(os.path.join(HERE, 'output', 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((music * 32767).astype(np.int16).tobytes())

# ダッキング: ナレーションの包絡(50ms RMS, リリース約0.5秒)で BGM を下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, len(voice) - len(rms) * hop))
speech = np.clip(env / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.17
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(HERE, 'output', 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())

# アップロード向け: -14 LUFS に正規化・ステレオ AAC
import subprocess, json, re
LN = 'loudnorm=I=-14:TP=-1.5:LRA=11'
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', MIX, '-af', 'pan=stereo|c0=c0|c1=c0,' + LN + ':print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True, check=True)
m = json.loads(re.search(r'\{[^{}]*\}\s*$', r.stderr).group(0))
af = f"pan=stereo|c0=c0|c1=c0,volume={-14 - float(m['input_i']):.2f}dB,alimiter=limit=0.84:level=false"  # -14 LUFS へゲイン調整(ピークは -1.5dBFS 付近で抑える)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX, '-map', '0:v', '-map', '1:a',
                '-c:v', 'copy', '-af', af, '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
