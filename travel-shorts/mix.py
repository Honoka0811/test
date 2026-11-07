# -*- coding: utf-8 -*-
"""ナレーション(output/narration.wav) + BGM(bgm.py, ダッキング) + 効果音(sfx.py) をミックスし、
output/mix.wav を書き出す。output/video_silent.mp4 があれば合成して output/video_narrated.mp4 を作る。
使い方: python3 mix.py
"""
import os, json, wave, subprocess
import numpy as np
import bgm, sfx

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'output')
SR = 48000
TL = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
TOTAL = TL['total']; N = int(TOTAL * SR)
S = {sc['id']: sc for sc in TL['scenes']}

def read_wav(p):
    with wave.open(p) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
def write_wav(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
def put(buf, t, sig, g=1.0):
    s = int(t * SR); e = min(s + len(sig), len(buf))
    if 0 <= s < e: buf[s:e] += sig[:e - s] * g

# ---------- ナレーション ----------
voice = read_wav(os.path.join(OUT, 'narration.wav'))
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]

# ---------- BGM: 5位でドロップ、2位の終わりで一旦抜いて1位で再ドロップ ----------
r5, r1, cta = S['r5']['start'], S['r1']['start'], S['cta']['start']
music = bgm.generate(TOTAL + 1, drops=(r5, r1), risers=((r5, 1.4), (r1, 2.2)), breakdown=(r1 - 2.2, r1), outro=TOTAL - 2.5)[:N]

# ---------- 効果音 ----------
fx = np.zeros(N, dtype=np.float32)
for sc in TL['scenes']:
    if sc['start'] > 0:
        put(fx, sc['start'] - 0.22, sfx.whoosh(0.5, seed=int(sc['start'])), 0.8)   # シーン切替のウーッシュ
    if sc.get('rank'):
        put(fx, sc['start'] + 0.05, sfx.pop(700), 0.7)                                # 順位バッジ
        put(fx, sc['start'] + 0.22, sfx.pop(1100, 0.07), 0.45)                        # 地名スライドイン
# コールアウト(render.html の CALLOUTS と同じフレーズ位置)
CALL = {'r5': [(1, 1, 'counter'), (2, 0, 'pill')], 'r4': [(1, 0, 'counter'), (2, 0, 'pill')],
        'r3': [(1, 1, 'pill'), (2, 1, 'pill')], 'r2': [(1, 1, 'pill'), (2, 0, 'counter'), (2, 1, 'pill')],
        'r1': [(1, 0, 'pill'), (2, 0, 'pill')]}
for sid, items in CALL.items():
    for si, pi, kind in items:
        at = S[sid]['sentences'][si]['phrases'][pi]['start'] - 0.05
        put(fx, at, sfx.pop(900), 0.6)
        if kind == 'counter':
            for k in range(12): put(fx, at + 0.05 + k * 0.07, sfx.tick(), 0.35 * (1 - k / 14))   # カウンターの刻み
            put(fx, at + 0.9, sfx.ding(1568), 0.55)
# フック: 「5選」バースト、1位: 鏡になる瞬間のきらめき、CTA ボタン
hook = S['hook']; put(fx, hook['sentences'][1]['phrases'][1]['start'] - 0.15, sfx.boom(), 0.8); put(fx, hook['sentences'][1]['phrases'][1]['start'] - 0.1, sfx.sparkle(1.2, 5), 0.5)
put(fx, 0.0, sfx.boom(0.8), 0.6)
put(fx, S['r1']['sentences'][1]['phrases'][1]['start'] + 0.05, sfx.sparkle(1.6, 3), 0.8)
put(fx, S['r1']['sentences'][1]['phrases'][1]['start'] + 0.1, sfx.ding(2093), 0.4)
c = S['cta']; put(fx, c['sentences'][1]['start'] + 0.3, sfx.pop(1200, .08), 0.6); put(fx, c['sentences'][2]['start'], sfx.pop(1200, .08), 0.6); put(fx, c['sentences'][2]['start'] + 0.6, sfx.pop(1400, .08), 0.6)

# ---------- ダッキング(ナレーション中は BGM を下げる) ----------
hop = SR // 20
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.88)
env = np.pad(np.repeat(env, hop), (0, N - len(rms) * hop))
speech = np.clip(env / 0.10, 0, 1)
BGM_FREE, BGM_DUCK = 0.42, 0.085
gain = BGM_FREE - (BGM_FREE - BGM_DUCK) * speech
k = SR // 12; gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice * 1.0 + music * gain + fx * 0.55
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.97)
write_wav(os.path.join(OUT, 'bgm.wav'), music * 0.95)
write_wav(os.path.join(OUT, 'mix.wav'), mixed)
print('wrote output/mix.wav', round(TOTAL, 2), 's')

src = os.path.join(OUT, 'video_silent.mp4'); dst = os.path.join(OUT, 'video_narrated.mp4')
if os.path.exists(src):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', os.path.join(OUT, 'mix.wav'),
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
    print('wrote', dst)
