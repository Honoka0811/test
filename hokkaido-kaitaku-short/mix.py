# -*- coding: utf-8 -*-
"""ナレーション + BGM(発話中は自動で音量を下げる)をミックスし、無音の映像に合成して
-14 LUFS に正規化した最終 mp4 を out/ に書き出す。"""
import json, os, re, subprocess, wave
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
O = lambda *p: os.path.join(HERE, *p)
tl = json.loads(re.sub(r'^window\.TIMELINE = |;\s*$', '', open(O('timeline.js'), encoding='utf-8').read()))
cue = {c['id']: c for c in tl['cues']}
with wave.open(O('audio', 'narration.wav')) as w:
    voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
# 打音: 「実は」の直前と、各シーンの切り替わり
mid = lambda a, b: (cue[a]['end'] + cue[b]['start']) / 2
hits = [cue['hook3']['start'] - 0.12, mid('hook3', 'jomon1'), mid('jomon4', 'road1'), mid('road4', 'shu1'), mid('shu2', 'end1')]
music = bgm.generate(tl['total'], hits)
music = np.pad(music, (0, max(0, len(voice) - len(music))))[:len(voice)]
with wave.open(O('audio', 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((music * 32767).astype(np.int16).tobytes())
# ダッキング: ナレーションの包絡(50ms RMS、リリース約0.5秒)に応じて BGM を下げる
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, len(voice) - len(rms) * hop))
speech = np.clip(env / 0.10, 0, 1)
gain = 0.55 - (0.55 - 0.26) * speech
k = SR // 10; gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
with wave.open(O('audio', 'mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mixed * 32767).astype(np.int16).tobytes())
# -14 LUFS(YouTube 基準)に 2 パスで正規化して多重化
SRC, DST = O('out', 'video_silent.mp4'), O('out', 'hokkaido_kaitaku_bones_short.mp4')
m = subprocess.run(['ffmpeg', '-hide_banner', '-i', O('audio', 'mix.wav'), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
af = f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', O('audio', 'mix.wav'), '-c:v', 'libx264', '-crf', '23', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-af', af, '-ac', '2', '-ar', '48000',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
