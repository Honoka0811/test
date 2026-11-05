# -*- coding: utf-8 -*-
"""ナレーション + BGM(ナレーション中は自動で音量を下げる) + 効果音 をミックスし、映像と合成する。
使い方: python3 mix.py [入力mp4(無音)] [出力mp4]
"""
import os, sys, json, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'stress_relief_top10.mp4')
SR = bgm.SR

tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
with wave.open(os.path.join(OUT, 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
n = len(voice)
music = bgm.generate(tl)[:, :n]
sfx = bgm.render_sfx(tl)[:, :n]
music = np.pad(music, ((0, 0), (0, n - music.shape[1])))
sfx = np.pad(sfx, ((0, 0), (0, n - sfx.shape[1])))

# BGM 書き出し(単体)
def write(path, x):
    x = np.atleast_2d(x)
    with wave.open(path, 'wb') as w:
        w.setnchannels(x.shape[0]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x.T, -1, 1) * 32767).astype(np.int16).tobytes())
write(os.path.join(OUT, 'bgm.wav'), music)

# ダッキング: ナレーションの包絡(20ms RMS、アタック速め/リリース約0.4秒)で BGM を下げる
hop = SR // 50
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0) * 0.95)
envl = np.pad(np.repeat(envl, hop), (0, n - len(envl) * hop))
speech = np.clip(envl / 0.08, 0, 1)
G_SILENT, G_SPEECH = 0.55, 0.17
gain = G_SILENT - (G_SILENT - G_SPEECH) * speech
k = SR // 20
gain = np.convolve(gain, np.ones(k) / k, mode='same').astype(np.float32)

mix = music * gain + sfx * 0.9 + voice[None, :] * 1.0
peak = np.max(np.abs(mix))
# ソフトリミッター(0.8 を超えた分だけ滑らかに圧縮。全体の音量は下げない)
a = np.abs(mix); T = 0.8
mix = np.where(a < T, mix, np.sign(mix) * (T + 0.18 * np.tanh((a - T) / 0.18)))
MIXW = os.path.join(OUT, 'mix.wav')
write(MIXW, mix)
print('wrote', MIXW, f'peak={peak:.2f}')

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIXW, '-map', '0:v', '-map', '1:a',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
