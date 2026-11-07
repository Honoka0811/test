# -*- coding: utf-8 -*-
"""ナレーション + BGM(ナレーション中は自動で音量を下げる) + 効果音 をミックスして output/mix.wav(48kHz ステレオ)を作る。"""
import os, wave
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__)); SR = bgm.SR
T = bgm.load_timing(); n = int(T['total'] * SR)

with wave.open(os.path.join(HERE, 'output', 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]
music = bgm.generate(T)[:n]
fx = bgm.sfx(T)[:n]

# ダッキング: ナレーションの包絡(20ms RMS、アタック速く/リリース 0.35 秒)で BGM を下げる
hop = SR // 50
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * .89)
env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
speech = np.clip(env / .08, 0, 1)
MUSIC_FREE, MUSIC_UNDER = .42, .17          # 発話していない時 / 発話中 の BGM ゲイン
gain = MUSIC_FREE - (MUSIC_FREE - MUSIC_UNDER) * speech
gain = np.convolve(gain, np.ones(SR // 20) / (SR // 20), mode='same')

mix = voice[:, None] * 1.0 + music * gain[:, None] + fx * .32
mix = np.tanh(mix * 1.1) / np.tanh(1.1)      # 軽いソフトクリップでピークを丸める
mix /= max(1.0, np.max(np.abs(mix)) / .97)
for name, x in (('mix.wav', mix), ('bgm.wav', music), ('sfx.wav', fx)):
    with wave.open(os.path.join(HERE, 'output', name), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
print('wrote output/mix.wav, output/bgm.wav, output/sfx.wav', f'{n / SR:.2f}s')
