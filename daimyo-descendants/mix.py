# -*- coding: utf-8 -*-
"""BGM(bgm.py)をナレーションに合わせてダッキングしながらミックスし、映像と合成する。
output/narration.wav が無い場合は BGM だけのプレビュー版を作る。
使い方: python3 mix.py  -> output/mix.wav, output/daimyo_descendants.mp4(または preview_no_voice.mp4)
"""
import os, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = bgm_mod.SR
tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
total = tl['total']
n = int(total * SR)

nar_path = os.path.join(OUT, 'narration.wav')
has_voice = os.path.exists(nar_path) and not tl.get('estimated')
if has_voice:
    with wave.open(nar_path) as w:
        voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
else:
    voice = np.zeros(n, np.float32)
voice = voice[:n] if len(voice) >= n else np.pad(voice, (0, n - len(voice)))

music = bgm_mod.generate(total)
music = music[:n] if len(music) >= n else np.pad(music, (0, n - len(music)))

# 字幕の発話区間からダッキング用のゲインを作る(発話中は下げ、間では少し戻す)
speech = np.zeros(n, np.float32)
for sc in tl['scenes']:
    for ln in sc['lines']:
        speech[int(ln['start'] * SR):int(ln['end'] * SR)] = 1
k = int(0.35 * SR)
speech = np.convolve(speech, np.ones(k) / k, mode='same')
speech = np.clip(speech * 1.5, 0, 1)
BGM_GAP, BGM_SPEECH = 0.34, 0.15
gain = BGM_GAP - (BGM_GAP - BGM_SPEECH) * speech
if not has_voice:
    gain = np.full(n, 0.6, np.float32)
mixed = voice + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
mix_path = os.path.join(OUT, 'mix.wav')
with wave.open(mix_path, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())

video = os.path.join(OUT, 'video_silent.mp4')
dst = os.path.join(OUT, 'daimyo_descendants.mp4' if has_voice else 'preview_no_voice.mp4')
# 音量を YouTube 基準(-14 LUFS)に合わせ、ステレオ AAC で多重化
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video, '-i', mix_path, '-map', '0:v', '-map', '1:a',
                '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ac', '2', '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst, '(with narration)' if has_voice else '(BGM only preview)')
