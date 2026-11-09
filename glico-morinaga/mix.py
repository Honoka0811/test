# -*- coding: utf-8 -*-
"""BGM(bgm.py)を生成し、ナレーション中は自動で音量を下げて(ダッキング)ミックス、
無音動画に合成して -14 LUFS(ステレオAAC)で最終書き出しする。
使い方: python3 mix.py  (先に narrate.py と capture.js を実行しておく)
"""
import os, re, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
T = json.loads(re.search(r'window\.TIMINGS = (.*);', open(os.path.join(HERE, 'timings.js'), encoding='utf-8').read(), re.S).group(1))

def read_wav(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
def write_wav(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

voice = read_wav(os.path.join(OUT, 'narration.wav'))
hits = [s['start'] for s in T['scenes'][1:-1]]       # シーン切替に衝撃音
music = bgm_mod.generate(T['total'], hits=hits)
n = min(len(voice), len(music)); voice, music = voice[:n], music[:n]
write_wav(os.path.join(OUT, 'bgm.wav'), music)

# ダッキング: ナレーションの包絡に応じて BGM を下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, n - n // hop * hop))
speech = np.clip(env / 0.10, 0, 1)
gain = 0.55 - (0.55 - 0.22) * speech
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
mix = voice + music * gain
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.95)
write_wav(os.path.join(OUT, 'mix.wav'), mix)

src = os.path.join(OUT, 'glico_morinaga_silent.mp4')
dst = os.path.join(OUT, 'glico_morinaga_short.mp4')
meas = subprocess.run(['ffmpeg', '-hide_banner', '-i', os.path.join(OUT, 'mix.wav'), '-af',
                       'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                      capture_output=True, text=True).stderr
m = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', os.path.join(OUT, 'mix.wav'),
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
print('wrote', dst)
