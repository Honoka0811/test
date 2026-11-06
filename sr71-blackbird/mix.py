# -*- coding: utf-8 -*-
"""ナレーション + BGM + 効果音をミックスして無音動画に合成し、アップロード用に書き出す。
- BGM はナレーション中に自動で下げる(ダッキング)。声のない「間」では BGM と効果音が前に出る
- YouTube の基準 -14 LUFS / True Peak -1.5 dB に 2 パスで正規化
出力: output/mix.wav, upload/sr71_blackbird_short.mp4
"""
import json, os, subprocess, wave
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
UP = os.path.join(HERE, 'upload')
os.makedirs(UP, exist_ok=True)
SR = bgm.SR

tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
music, sfx = bgm.generate(tl)
n = len(music)
voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]

# ナレーションの包絡 → BGM のゲイン(アタック速め、リリース 0.35 秒)
hop = SR // 100
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.972)
env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
speech = np.clip(env / 0.08, 0, 1)
k = SR // 25
speech = np.convolve(speech, np.ones(k) / k, mode='same')
g_music = 0.62 - (0.62 - 0.17) * speech
g_sfx = 0.75 - (0.75 - 0.25) * speech

# 声を少しだけ前に出す(120Hz 以下カット + 軽いコンプ)
v = bgm.hp(voice, 120)
v = np.tanh(v * 1.6) / np.tanh(1.6)
bg = music * g_music[:, None] + sfx * g_sfx[:, None]
for sc in tl['scenes']:  # 発話中の 声 / 背景 の比(確認用)
    a, b = int(sc['chunks'][0]['start'] * SR), int(sc['chunks'][0]['end'] * SR)
    r = np.sqrt(np.mean(v[a:b] ** 2)) / (np.sqrt(np.mean(bg[a:b] ** 2)) + 1e-9)
    print(f"  {sc['id']:9s} voice/bg {20 * np.log10(r):5.1f} dB")
mix = np.stack([v, v], axis=1) + bg
mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
bgm.write_wav(os.path.join(OUT, 'mix.wav'), mix)
print('wrote output/mix.wav')

src = os.path.join(OUT, 'video_silent.mp4')
dst = os.path.join(UP, 'sr71_blackbird_short.mp4')
m = subprocess.run(['ffmpeg', '-hide_banner', '-i', os.path.join(OUT, 'mix.wav'), '-af',
                    'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
      f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', src, '-i', os.path.join(OUT, 'mix.wav'),
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af, '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
