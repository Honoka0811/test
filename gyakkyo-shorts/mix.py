# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング) + SFX をミックスし、無音動画に合成する。
使い方: python3 mix.py [無音mp4] [出力mp4]
"""
import sys, os, wave, json, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'gyakkyo_shorts.mp4')
SR = 48000
def rd(p):
    with wave.open(p) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
nar = rd(os.path.join(OUT, 'narration.wav'))
import bgm as bgm_mod
tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
music, sfx = bgm_mod.generate(tl)
bgm_mod.write(os.path.join(OUT, 'bgm.wav'), music); bgm_mod.write(os.path.join(OUT, 'sfx.wav'), sfx)
n = len(nar)
fit = lambda x: x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))
music, sfx = fit(music), fit(sfx)
# ナレーション包絡でダッキング(発話時 BGM を約 -8dB)
hop = SR // 20
rms = np.sqrt(np.mean(nar[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, n - len(env) * 1 if len(env) * hop < n else 0))[:n]
speech = np.clip(env / 0.10, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.34, 0.14
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 8; gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = nar * 1.0 + music * gain + sfx * 0.45
# ソフトリミッタ
mixed = np.tanh(mixed * 1.1) / np.tanh(1.1)
mixed /= max(1.0, np.max(np.abs(mixed)) / 0.97)
MIX = os.path.join(OUT, 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
