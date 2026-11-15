# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング)+ 効果音(シーン切替のシュッ・順位表示のキラン)をミックスし、
無音動画に合成して最終 mp4 を作る。
使い方: python3 mix.py   (先に narrate.py と node capture.js を実行しておく)
"""
import os, re, json, wave, subprocess
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000

def read_wav(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

def write_wav(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

tl = json.loads(re.search(r'=\s*(\{.*\});', open(os.path.join(OUT, 'timeline.js'), encoding='utf-8').read(), re.S).group(1))
TOTAL = tl['total']
voice = read_wav(os.path.join(OUT, 'narration.wav'))
N = int(TOTAL * SR)
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]

# ---------- 効果音 ----------
rng = np.random.default_rng(3)
def whoosh(dur=0.45):
    t = np.arange(int(dur * SR)) / SR
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n); k0, k1 = 40, 4  # 平均化幅を狭めて「こもり → 明るい」へスイープ
    for i, (a, b) in enumerate(zip(np.linspace(0, len(t), 9)[:-1].astype(int), np.linspace(0, len(t), 9)[1:].astype(int))):
        k = int(k0 + (k1 - k0) * i / 7)
        out[a:b] = np.convolve(n, np.ones(k) / k, mode='same')[a:b]
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (out * env * 1.2).astype(np.float32)

def sparkle():
    t = np.arange(int(0.7 * SR)) / SR
    s = np.zeros_like(t)
    for i, f in enumerate([1568, 2093, 2637, 3136]):  # G6 C7 E7 G7 のアルペジオ
        tt = t - i * 0.045
        s += np.where(tt > 0, np.sin(2 * np.pi * f * tt) * np.exp(-np.clip(tt, 0, None) / 0.18), 0)
    return (s * 0.35).astype(np.float32)

def fanfare():
    t = np.arange(int(1.2 * SR)) / SR
    s = np.zeros_like(t)
    for i, m in enumerate([72, 76, 79, 84]):
        f = 440 * 2 ** ((m - 69) / 12); tt = t - i * 0.09
        tone = sum((1 / h) * np.sin(2 * np.pi * f * h * np.clip(tt, 0, None)) for h in range(1, 5))
        s += np.where(tt > 0, tone * np.exp(-np.clip(tt, 0, None) / (0.5 if i == 3 else 0.15)), 0)
    return (s * 0.22).astype(np.float32)

sfx = np.zeros(N, dtype=np.float32)
def add(t0, sig, g):
    s = int(t0 * SR); e = min(N, s + len(sig))
    if e > s: sfx[s:e] += g * sig[:e - s]
W_, S_, F_ = whoosh(), sparkle(), fanfare()
for i, sc in enumerate(tl['scenes']):
    if i > 0: add(sc['start'] - 0.05, W_, 0.35)
    if sc['id'] == 'r1': add(sc['start'] + 0.15, F_, 0.9)
    elif sc['id'].startswith('r'): add(sc['start'] + 0.15, S_, 0.6)

# ---------- BGM(ナレーション中は自動で音量を下げる) ----------
music = bgm_mod.generate(TOTAL)
music = np.pad(music, (0, max(0, N - len(music))))[:N]
hop = SR // 20
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
envl = np.pad(np.repeat(envl, hop), (0, N - len(rms) * hop))
speech = np.clip(envl / 0.1, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.34, 0.16
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')

mixed = voice + music * gain + sfx
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
write_wav(os.path.join(OUT, 'bgm.wav'), music)
write_wav(os.path.join(OUT, 'mix.wav'), mixed)

SRC = os.path.join(OUT, 'video_silent.mp4')
DST = os.path.join(OUT, 'osaka_univ_top10.mp4')
# -14 LUFS(YouTube 基準)に 2 パスで正規化し、ステレオ AAC で多重化
m = subprocess.run(['ffmpeg', '-hide_banner', '-i', os.path.join(OUT, 'mix.wav'), '-af',
                    'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
      f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', os.path.join(OUT, 'mix.wav'), '-map', '0:v', '-map', '1:a',
                '-c:v', 'copy', '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
