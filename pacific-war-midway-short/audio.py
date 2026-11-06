# -*- coding: utf-8 -*-
"""BGM と効果音をすべて numpy/scipy で合成し(外部音源なし・権利フリー)、ナレーションとミックスする。
- BGM: 映画予告風のテンション曲(Dマイナー / 120BPM)。シーン構成(timeline.json)に合わせて
  「ブラーム → 刻むオスティナート → 太鼓で盛り上げ → 急降下直前に無音 → 爆発 → 余韻」と展開する。
- 効果音: render.html と同じイベント表(events.json)の時刻に配置するので映像と完全に同期する。
- ナレーション中は BGM を自動で下げる(ダッキング)。
出力: output/bgm.wav, output/sfx.wav, output/final_mix.wav(ステレオ 48kHz)
"""
import os, json, wave
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
BPM = 120
BEAT = 60 / BPM
rng = np.random.default_rng(42)

tl = json.load(open(os.path.join(OUT, 'timeline.json'), encoding='utf-8'))
events = json.load(open(os.path.join(OUT, 'events.json'), encoding='utf-8'))
DUR = tl['duration']
N = int(np.ceil(DUR * SR)) + SR
S = {s['id']: s for s in tl['scenes']}
S['hook']['start'] = 0.0

def read_wav(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

def write_wav(p, x, ch=1):
    x = np.clip(x, -1, 1)
    with wave.open(p, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def noise(d): return rng.standard_normal(int(d * SR)).astype(np.float32)
def add(buf, t0, sig, gain=1.0):
    s = int(t0 * SR)
    if s < 0: sig = sig[-s:]; s = 0
    e = min(len(buf), s + len(sig))
    if e > s: buf[s:e] += gain * sig[:e - s]
def env(n, a, r, hold=None):
    e = np.ones(n, dtype=np.float32); na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[n - nr:] *= np.linspace(1, 0, nr)
    return e
def saw(f, t, det=0.0):
    ph = (f * (1 + det) * t + rng.random()) % 1.0
    return 2 * ph - 1
def norm(x, peak=1.0): return x / (np.max(np.abs(x)) + 1e-9) * peak

# ================= 楽器 =================
def braam(d=3.0, root=38):
    """映画予告の「ブォーン」: 低いデチューンSAWの和音 + フィルタが開いて閉じる"""
    t = tt(d); x = np.zeros_like(t)
    for n in (root - 12, root, root + 7, root + 12, root + 15):
        for det in (-.006, 0, .006):
            x += saw(midi(n), t, det) * (1.0 if n < root + 8 else .5)
    # フィルタの開閉: 暗い音と明るい音をクロスフェード
    k = t / d; m = np.exp(-k * 5) * np.minimum(1, k * 30)
    out = lp(x, 180) * (1 - m) + lp(x, 2600) * m
    return norm(out * env(len(t), .02, d * .7) * np.exp(-t * .6), .9).astype(np.float32)

def sub_boom(d=2.2, f0=70, f1=28):
    t = tt(d); f = f1 + (f0 - f1) * np.exp(-t / .15)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .7)
    x += lp(noise(d), 400) * np.exp(-t / .08) * .6
    return norm(x, .95).astype(np.float32)

def taiko(f0=95, d=.8, amp=1.0):
    t = tt(d); f = 48 + (f0 - 48) * np.exp(-t / .07)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .25)
    click = lp(noise(d), 1800) * np.exp(-t / .015)
    return (amp * norm(body + .35 * click)).astype(np.float32)

def snare(d=.35, amp=1.0):
    t = tt(d); x = bp(noise(d), 1500, 7000) * np.exp(-t / .07) + .4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / .05)
    return (amp * norm(x)).astype(np.float32)

def hat(d=.06, amp=1.0):
    t = tt(d); return (amp * norm(hp(noise(d), 7000) * np.exp(-t / .015))).astype(np.float32)

def pluck_bass(note, d=.24):
    t = tt(d); f = midi(note)
    x = saw(f, t) + .6 * saw(f, t, .004) + .5 * np.sin(2 * np.pi * f / 2 * t)
    x = lp(x, 900) * env(len(t), .004, .05) * np.exp(-t / .18)
    return norm(x, .9).astype(np.float32)

def string_stab(notes, d=.6):
    t = tt(d); x = sum(saw(midi(n), t, det) for n in notes for det in (-.004, .004))
    x = lp(x, 2500) * env(len(t), .01, .3) * np.exp(-t / .3)
    return norm(x, .8).astype(np.float32)

def pad(notes, d):
    t = tt(d); x = np.zeros_like(t)
    for n in notes:
        for det in (-.005, 0, .005):
            for h in range(1, 6):
                x += np.sin(2 * np.pi * midi(n) * h * (1 + det) * t + rng.random() * 6.28) / h ** 1.6
    return norm(x * env(len(t), d * .3, d * .4), .8).astype(np.float32)

def bell(note, d=2.0):
    t = tt(d); f = midi(note)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (dd)) for r, a, dd in ((1, 1, .9), (2.76, .5, .4), (5.4, .25, .2)))
    return norm(x, .8).astype(np.float32)

def riser(d=2.0):
    t = tt(d); k = t / d
    f = 200 + 2800 * k ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * .3
    nz = noise(d); bands = [bp(nz, f * .7, f * 1.4) for f in (400, 1200, 3500, 8000)]
    pos = np.clip(k * 3, 0, 3); out = np.zeros_like(nz)
    for j, b in enumerate(bands): out += b * np.clip(1 - np.abs(pos - j), 0, 1)
    return norm((out + tone) * k ** 1.5, .8).astype(np.float32)

# ================= BGM =================
music = np.zeros(N, dtype=np.float32)
drums = np.zeros(N, dtype=np.float32)
pads = np.zeros(N, dtype=np.float32)

# 冒頭のブラーム + サブドロップ
add(music, 0.0, braam(3.5), 1.0)
add(drums, 0.0, sub_boom(2.5), 1.0)

# オスティナート(8分音符の刻み)。Dm → Bb → Gm → A のループ、2小節ごとに和音が変わる
ROOT_SEQ = [38, 34, 31, 33]   # D2, Bb1, G1, A1
PATTERN = [0, 0, 12, 0, 0, 7, 0, 10]
o_start, o_end = S['hook']['chunks'][1]['start'], S['attack']['chunks'][1]['end'] + .05
silence = next(e for e in events if e['type'] == 'silence')
t = o_start; i = 0
while t < o_end:
    bar = int((t - o_start) / (BEAT * 4)); root = ROOT_SEQ[(bar // 2) % 4]
    sc_t = t
    vel = .55 if t < S['code']['start'] else (.75 if t < S['rearm']['start'] else .9)
    if t < S['hook']['end']: vel = .4
    add(music, t, pluck_bass(root + PATTERN[i % 8]), vel)
    t += BEAT / 2; i += 1

# ハイハット(16分) — 暗号シーン以降
t = S['code']['start']; i = 0
while t < o_end:
    acc = 1.0 if i % 4 == 0 else (.5 if i % 2 == 0 else .3)
    add(drums, t, hat(), .22 * acc)
    t += BEAT / 4; i += 1

# 太鼓とスネア — 罠以降は 1・3 拍、待ち伏せ以降は倍に
t = S['empire']['start']; i = 0
while t < o_end:
    beat = i % 4
    if beat in (0,) or (t > S['trap']['start'] and beat == 2):
        add(drums, t, taiko(), .85)
    if t > S['rearm']['start']:
        if beat in (1, 3): add(drums, t, snare(), .45)
        add(drums, t + BEAT / 2, taiko(80, .5), .4)
    t += BEAT; i += 1

# ストリングスの刻み(緊張感)— 罠〜攻撃
t = S['trap']['start']; i = 0
CH = {38: [62, 65, 69], 34: [58, 62, 65], 31: [58, 62, 67], 33: [57, 61, 64]}
while t < o_end:
    bar = int((t - o_start) / (BEAT * 4)); root = ROOT_SEQ[(bar // 2) % 4]
    if i % 2 == 0: add(music, t, string_stab(CH[root], .22), .28)
    t += BEAT / 2; i += 1

# ライザー: バレる直前と、待ち伏せ直前
add(music, S['bite']['chunks'][2]['start'] + .7 - 2.0, riser(2.0), .45)
add(music, S['rearm']['start'] - 1.6, riser(1.6), .35)

# 6分シーン: 大太鼓の連打 + 低音パッド
six = S['six']
add(pads, six['start'], pad([38, 45, 50, 53], six['end'] - six['start'] + 1), .6)
t = six['start']; i = 0
while t < six['end'] - .2:
    add(drums, t, taiko(100 if i % 4 == 0 else 85, .8), 1.0 if i % 2 == 0 else .65)
    if i % 2 == 1: add(drums, t, snare(), .35)
    t += BEAT; i += 1

# エンディング: 静かなパッド Dm → Bb → F → A
end = S['end']; seg = (end['end'] - end['start']) / 4
for k, ch in enumerate([[50, 53, 57], [46, 50, 53], [45, 48, 53], [45, 49, 52]]):
    add(pads, end['start'] + k * seg, pad(ch, seg + 1.2), .55)
for k, n in enumerate([74, 72, 69, 74]):
    add(pads, end['start'] + .3 + k * seg, bell(n, 2.5), .25)

bgm = norm(music * .55 + drums * .6 + pads * .5, .9)
# 急降下直前の無音(BGMを一気に切る)→ 爆発で6分シーンへ
g = np.ones(N, dtype=np.float32)
s0 = int(silence['t'] * SR); s1 = int((six['start']) * SR)
fade = int(.08 * SR)
g[s0:s1] = 0; g[s0 - fade:s0] = np.linspace(1, 0, fade)
bgm *= g
bgm[:N] *= env(N, .01, 2.5)

# ================= 効果音 =================
sfx = np.zeros(N, dtype=np.float32)
def whoosh(d=.45):
    t = tt(d); k = t / d; nz = noise(d)
    m = np.sin(np.pi * k); out = bp(nz, 300, 900) * (1 - m) + bp(nz, 1500, 7000) * m
    return norm(out * np.sin(np.pi * k) ** 2, .8)
def stamp_sfx():
    return norm(np.concatenate([taiko(130, .5)]) + np.pad(hp(noise(.03), 2000) * .5, (0, int(.47 * SR))), .95)
def glitch(d):
    t = tt(d); x = np.sign(np.sin(2 * np.pi * (300 + 1500 * rng.random()) * t)) * .3
    x *= (np.floor(t * 40) % 2); x += hp(noise(d), 3000) * .3 * (np.floor(t * 23) % 2)
    return norm(x, .5)
def beep(f, d, a=.003):
    t = tt(d); return (np.sin(2 * np.pi * f * t) * env(len(t), a, a)).astype(np.float32)
def morse(d):
    out = np.zeros(int(d * SR) + SR, dtype=np.float32); t = 0; i = 0
    pat = '.-- .- - . .-. ..-. .- .. .-.. . -.. .--. .-.. .- -. -'
    while t < d:
        c = pat[i % len(pat)]
        if c == '.': add(out, t, beep(760, .07), .5); t += .14
        elif c == '-': add(out, t, beep(760, .2), .5); t += .27
        else: t += .14
        i += 1
    return out[:int(d * SR)]
def radio(d):
    t = tt(d); x = bp(noise(d), 800, 3000) * .25 * (1 + .5 * np.sin(2 * np.pi * 7 * t))
    return (x * env(len(t), .05, .3)).astype(np.float32)
def stinger():
    t = tt(1.4); x = sum(saw(midi(n), t, det) for n in (74, 75, 81) for det in (-.003, .003))
    return norm(lp(x, 5000) * env(len(t), .01, 1.0) * (1 + .3 * np.sin(2 * np.pi * 6 * t)), .5)
def lock():
    out = np.zeros(int(.9 * SR), dtype=np.float32)
    for k, tt0 in enumerate((0, .12, .24)): add(out, tt0, beep(1800, .06), .4)
    add(out, .36, beep(1800, .4), .5); return out
def alarm(d):
    t = tt(d); f = np.where((t * 2.5) % 1 < .5, 660, 520)
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * .25
    return (lp(x, 3000) * env(len(t), .02, .2)).astype(np.float32)
def flak():
    return norm(lp(noise(.5), 1500) * np.exp(-tt(.5) / .06) + .5 * taiko(70, .5), .7)
def heartbeat(d):
    out = np.zeros(int(d * SR) + SR, dtype=np.float32); t = 0
    while t < d: add(out, t, taiko(60, .4), .8); add(out, t + .22, taiko(55, .4), .55); t += .85
    return out
def whistle(d):
    t = tt(d); f = 1700 * np.exp(-t / d * 1.4) + 350
    f = f * (1 + .01 * np.sin(2 * np.pi * 9 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / d) ** .6 + .15 * bp(noise(d), 1500, 4000) * (t / d)
    return norm(x * env(len(t), .05, .05), .55)
def explode(d=2.4, big=1.0):
    t = tt(d); x = lp(noise(d), 900 + 1500 * big) * np.exp(-t / (.35 * big + .2))
    x += .8 * sub_boom(d, 60, 25)[:len(t)]
    crackle = hp(noise(d), 2500) * (rng.random(len(t)) > .995) * 3 * np.exp(-t / 1.0)
    return norm(x + crackle, .95)
def tick(): return norm(hp(noise(.02), 3000) * np.exp(-tt(.02) / .003), .5)

for e in events:
    T, ty = e['t'], e['type']
    if ty == 'whoosh': add(sfx, T, whoosh(), .35)
    elif ty == 'boom': add(sfx, T, explode(2.8, 1.4), .9)
    elif ty == 'stamp': add(sfx, T, stamp_sfx(), .7)
    elif ty == 'marker': add(sfx, T, beep(1200, .12), .3)
    elif ty == 'glitch': add(sfx, T, glitch(e['dur']), .5)
    elif ty == 'stinger': add(sfx, T, stinger(), .5)
    elif ty == 'braam': add(sfx, T, braam(2.5, 38), .45)
    elif ty == 'radio': add(sfx, T, radio(e['dur']), .5)
    elif ty == 'morse': add(sfx, T, morse(e['dur']), .4)
    elif ty == 'lock': add(sfx, T - .36, lock(), .5)
    elif ty == 'alarm': add(sfx, T, alarm(e['dur']), .3)
    elif ty == 'pop': add(sfx, T, flak(), .45)
    elif ty == 'heartbeat': add(sfx, T, heartbeat(e['dur']), .5)
    elif ty == 'whistle': add(sfx, T, whistle(e['dur']), .55)
    elif ty == 'explode': add(sfx, T, explode(2.0, 1.0), .7)
    elif ty == 'ticks':
        k = 0
        while k * .09 < e['dur']: add(sfx, T + k * .09, tick(), .5); k += 1
    elif ty == 'ding': add(sfx, T, bell(81, 1.5), .3)

# ================= ミックス =================
voice = read_wav(os.path.join(OUT, 'voice.wav'))
voice = np.pad(voice, (0, N - len(voice)))[:N]
hop = SR // 50
rms = np.sqrt(np.mean(voice[:N // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms): envl[i] = max(v, (envl[i - 1] if i else 0) * .955)   # リリース約0.4秒
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, N - len(envl)))
speech = np.clip(envl / .08, 0, 1)
duck = 1 - .55 * speech                       # 発話中は BGM を約 -7dB
duck = np.convolve(duck, np.ones(SR // 25) / (SR // 25), mode='same')

voice_eq = voice + .25 * hp(voice, 2500)      # 声の明瞭度を少し上げる
mix = voice_eq * 1.0 + bgm * .42 * duck + sfx * .55 * (1 - .35 * speech)
mix = mix[:int(DUR * SR)]
# ソフトリミッター
mix = np.tanh(mix * 1.1) / np.tanh(1.1)

write_wav(os.path.join(OUT, 'bgm.wav'), bgm[:int(DUR * SR)] * .9)
write_wav(os.path.join(OUT, 'sfx.wav'), norm(sfx[:int(DUR * SR)], .9))
# 簡易ステレオ化: BGM/SFX に僅かなディレイ差を付けて広がりを出す(声はセンター)
d = int(.012 * SR)
side = np.pad((bgm * .42 * duck + sfx * .3)[:int(DUR * SR)], (d, 0))[:int(DUR * SR)]
L = mix + .12 * side; R = mix - .12 * side
st = np.stack([L, R], axis=1).reshape(-1)
write_wav(os.path.join(OUT, 'final_mix.wav'), st / max(1, np.max(np.abs(st)) / .97), ch=2)
print('wrote output/bgm.wav, sfx.wav, final_mix.wav', f'{DUR:.2f}s')
