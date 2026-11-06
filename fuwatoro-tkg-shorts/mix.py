# -*- coding: utf-8 -*-
"""ナレーション + BGM(ダッキング) + 効果音 をミックスし、無音の動画(output/video.mp4)に合成する。
使い方: python3 mix.py [入力mp4] [出力mp4]
"""
import os, sys, json, subprocess
import numpy as np
from dsp import *
import bgm, sfx

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'video.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'fuwatoro_tkg.mp4')

tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
TOTAL = tl['total']
S = {s['id']: s for s in tl['scenes']}
narr = read_wav(os.path.join(OUT, 'narration.wav'))
N = int(TOTAL * SR)
narr = np.pad(narr, (0, max(0, N - len(narr))))[:N]

# ---------- BGM(シーンに合わせて展開) ----------
music = bgm.generate(TOTAL, {'drop': S['promise']['start'], 'break': S['payoff']['start'], 'drop2': S['cta']['start']})
music = np.pad(music, (0, max(0, N - len(music))))[:N]
write_wav(os.path.join(OUT, 'bgm.wav'), music)

# ---------- 効果音キュー(シーン開始からの相対秒) ----------
rng = np.random.default_rng(11)
fxbuf = np.zeros(N, np.float32)
def cue(scene, rel, sig, gain=1.0): add(fxbuf, S[scene]['start'] + rel, sig, gain)
def cap_t(scene, i): return S[scene]['captions'][i]['start'] - S[scene]['start']   # i 番目のテロップ開始(相対)

# シーン切り替えのウーシュ + 各テロップのポップ音
for sc in tl['scenes']:
    if sc['id'] != 'hook': cue(sc['id'], -0.18, sfx.whoosh(rng, 0.38), 0.8)
    for c in sc['captions']:
        add(fxbuf, c['start'] - 0.02, sfx.pop(rng, 1100 if '*' in c['text'] else 800), 0.45)
# hook: 卵が落ちてバウンド → 「損」スタンプ
cue('hook', 0.55, sfx.plop(rng), 0.8); cue('hook', 0.95, sfx.plop(rng), 0.4)
cue('hook', cap_t('hook', 1) + 0.25, sfx.stamp(rng), 1.0)
# promise: キラキラ + 30秒バッジ
cue('promise', 0.35, sfx.sparkle(rng), 0.8); cue('promise', cap_t('promise', 1) + 0.1, sfx.ding(rng, 1568), 0.6)
# step1: ステップ音 → 卵が割れる → 2つに分かれてポトン×2
cue('step1', 0.05, sfx.ding(rng), 0.5); cue('step1', 0.95, sfx.crack(rng), 1.0)
cue('step1', cap_t('step1', 1) + 0.5, sfx.plop(rng), 0.6); cue('step1', cap_t('step1', 1) + 0.9, sfx.drip(rng, 900), 0.6)
# step2: ステップ音 → 白身ポトン → 混ぜる音(テンポ良く) → 30秒カウント → 成功のジャーン
cue('step2', 0.05, sfx.ding(rng), 0.5); cue('step2', 1.1, sfx.drip(rng, 800), 0.6)
t_mix = cap_t('step2', 1)
for i in range(14): cue('step2', t_mix + 0.1 + i * 0.19, sfx.stir(rng), 0.9 - 0.02 * i)
for i in range(4): cue('step2', t_mix + 0.3 + i * 0.5, sfx.tick(rng), 0.6)
cue('step2', cap_t('step2', 2) + 0.9, sfx.swell(rng), 0.9); cue('step2', cap_t('step2', 2) + 0.9, sfx.sparkle(rng, 1318), 0.5)
# step3: ステップ音 → くぼみ(ふわっ) → 黄身ポン → 醤油3滴 → バターじゅわ
cue('step3', 0.05, sfx.ding(rng), 0.5); cue('step3', 0.5, sfx.squish(rng), 0.8)
cue('step3', cap_t('step3', 0) + 1.25, sfx.plop(rng), 1.0)
t3 = cap_t('step3', 1)
for i in range(3): cue('step3', t3 + 0.75 + i * 0.3, sfx.drip(rng, 1700 - i * 150), 0.7)
cue('step3', cap_t('step3', 2) + 0.7, sfx.plop(rng), 0.5); cue('step3', cap_t('step3', 2) + 0.85, sfx.sizzle_melt(rng), 0.9)
# payoff: ブーム → 崩す(ふわっ) → キラキラ
cue('payoff', 0.0, sfx.boom(rng), 0.9); cue('payoff', 1.2, sfx.squish(rng), 1.0)
cue('payoff', cap_t('payoff', 1) - 0.05, sfx.sparkle(rng), 1.0); cue('payoff', cap_t('payoff', 1) + 0.5, sfx.swell(rng, 0.9), 0.6)
# cta: ポップ + ディン
cue('cta', 0.3, sfx.pop(rng, 700), 0.6); cue('cta', cap_t('cta', 1) + 0.3, sfx.ding(rng, 2093), 0.6)
fxbuf = norm(fxbuf, 0.8)
write_wav(os.path.join(OUT, 'sfx.wav'), fxbuf)

# ---------- ダッキング: ナレーション中は BGM を下げる ----------
hop = SR // 20
rms = np.sqrt(np.mean(narr[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0) * 0.88)
envl = np.pad(np.repeat(envl, hop), (0, N - len(envl) * hop))
speech = np.clip(envl / 0.10, 0, 1)
BGM_FREE, BGM_DUCK = 0.50, 0.22
gain = BGM_FREE - (BGM_FREE - BGM_DUCK) * speech
k = SR // 12; gain = np.convolve(gain, np.ones(k) / k, mode='same')

mixed = narr * 1.0 + music * gain + fxbuf * 0.55
mixed = soft_clip(mixed, 1.0) if np.max(np.abs(mixed)) > 1 else mixed
write_wav(os.path.join(OUT, 'mix.wav'), mixed / max(1.0, np.max(np.abs(mixed)) / 0.95))
print('wrote output/bgm.wav, sfx.wav, mix.wav')

if os.path.exists(SRC):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', os.path.join(OUT, 'mix.wav'),
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
    print('wrote', DST)
else:
    print('video not found, skipped mux:', SRC)
