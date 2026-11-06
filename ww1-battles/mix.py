# -*- coding: utf-8 -*-
"""BGM(G線上のアリア / アメリカ空軍バンド演奏・パブリックドメイン)とナレーションをミックスし、無音動画に合成する。
ナレーション中は BGM を自動で下げる(ダッキング)。output/narration.wav が無ければ BGM のみで書き出す(確認用)。
使い方: python3 mix.py [入力mp4] [出力mp4]
"""
import os, sys, json, wave, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'ww1_battles.mp4')
MUSIC = os.path.join(HERE, 'assets', 'air_usaf_band.mp3')
MUSIC_OFFSET = 4.3   # 録音冒頭の無音を飛ばす(演奏は約 4.5 秒から)
SR = 48000

dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', SRC],
                           capture_output=True, text=True, check=True).stdout)
n = int(round(dur * SR))

# BGM をデコード(ステレオ float32)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(MUSIC_OFFSET), '-i', MUSIC, '-t', str(dur + 1),
                      '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
music = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
music = music[:n] if len(music) >= n else np.pad(music, ((0, n - len(music)), (0, 0)))
music /= np.sqrt(np.mean(music ** 2)) + 1e-9          # RMS = 1 に揃える
fi, fo = int(0.4 * SR), int(4.0 * SR)                   # 0.4 秒フェードイン / 最後 4 秒フェードアウト
music[:fi] *= np.linspace(0, 1, fi)[:, None]
music[-fo:] *= (np.cos(np.linspace(0, np.pi, fo)) * 0.5 + 0.5)[:, None]

nar_path = os.path.join(OUT, 'narration.wav')
if os.path.exists(nar_path):
    with wave.open(nar_path) as w:
        assert w.getframerate() == SR
        voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    voice = voice[:n] if len(voice) >= n else np.pad(voice, (0, n - len(voice)))
else:
    print('narration.wav が無いため BGM のみで書き出します')
    voice = np.zeros(n, dtype=np.float32)

# ダッキング: ナレーションの包絡(50ms RMS、リリース約 0.6 秒)で BGM のゲインを下げる
hop = SR // 20
m = n // hop * hop
rms = np.sqrt(np.mean(voice[:m].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.92)
env = np.pad(np.repeat(env, hop), (0, n - m))
speech = np.clip(env / 0.08, 0, 1)
G_SILENT, G_SPEECH = 0.11, 0.045                        # BGM の RMS(無音時 / 発話時)
gain = G_SILENT - (G_SILENT - G_SPEECH) * speech
k = SR // 8
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mix = music * gain[:, None] + voice[:, None]
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)

MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
