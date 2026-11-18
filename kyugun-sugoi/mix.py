# -*- coding: utf-8 -*-
"""ナレーション(output/narration.wav)に BGM(bgm.py)と効果音を重ね、無音の映像と合成して完成動画を書き出す。
- 効果音は timeline.json の各セリフの sfx タグと、シーン切り替え(ワイプ)に合わせて numpy で合成する
- BGM はナレーション中に自動で下げる(ダッキング)。1位の発表直前は BGM を止めて「溜め」を作る
- 音量は -14 LUFS(YouTube 基準)に正規化する
使い方: python3 mix.py   →  output/kyugun_sugoi_short.mp4
"""
import os, json, wave, subprocess
import numpy as np
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SFX_OFF = {'fire': 0.12, 'hit': 0.6}   # render.html と同じ値
rng = np.random.default_rng(3)
tl = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))


def tt(d): return np.arange(int(d * SR)) / SR
def noise(d): return rng.standard_normal(int(d * SR)).astype(np.float32)
def lowpass(x, a):            # 1次ローパス(a が小さいほどこもる)
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)): acc += a * (x[i] - acc); y[i] = acc
    return y
def lp_fast(x, k):            # 移動平均による簡易ローパス
    return np.convolve(x, np.ones(k) / k, mode='same').astype(np.float32)

def boom(d=1.4, f0=55, drop=90):
    t = tt(d); f = f0 + drop * np.exp(-t * 18)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    x += lp_fast(noise(d), 24) * np.exp(-t * 9) * 1.2
    return np.tanh(x * 1.6).astype(np.float32)
def impact():                 # 順位の打ち込み: 低音 + 金属的なクラック
    d = 1.2; t = tt(d)
    x = boom(d, 48, 120) * 0.9
    crack = noise(d) * np.exp(-t * 40); crack -= lp_fast(crack, 6)
    ring = sum(np.sin(2 * np.pi * f * t) for f in (523, 787, 1180)) * np.exp(-t * 6) * 0.12
    return (x + crack * 0.6 + ring).astype(np.float32)
def pop():                    # 数字が出る音
    d = 0.35; t = tt(d)
    f = 900 + 700 * np.exp(-t * 40)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) + 0.4 * np.sin(2 * np.pi * 1760 * t) * np.exp(-t * 22)
    return (x * 0.6).astype(np.float32)
def whoosh(d=0.5):
    t = tt(d); n = noise(d)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    hi = n - lp_fast(n, 4); lo = lp_fast(n, 18)
    mixp = np.clip(t / d, 0, 1)     # 低→高へスイープ
    return ((lo * (1 - mixp) * 2.2 + hi * mixp) * env * 0.5).astype(np.float32)
def cannon():
    d = 2.6; t = tt(d)
    x = boom(d, 40, 140) * 1.0
    rumble = lp_fast(noise(d), 60) * np.exp(-t * 1.6) * 3.0
    blast = noise(d) * np.exp(-t * 25) * 0.7
    return np.tanh((x + rumble + blast) * 1.3).astype(np.float32)
def explosion():
    d = 2.4; t = tt(d)
    x = boom(d, 36, 100) + lp_fast(noise(d), 30) * np.exp(-t * 2.2) * 2.5
    splash = noise(d) * np.exp(-((t - 0.15) ** 2) / 0.04) * 0.35   # 水しぶき
    return np.tanh((x + splash) * 1.4).astype(np.float32)
def ping():                   # ソナー
    d = 2.2; t = tt(d)
    x = np.sin(2 * np.pi * 1480 * t) * np.exp(-t * 2.6) * np.minimum(t / 0.004, 1)
    for dl, gn in ((0.21, 0.4), (0.43, 0.22), (0.7, 0.12)):
        k = int(dl * SR); x[k:] += x[:-k] * gn
    return (x * 0.35).astype(np.float32)
def riser(d=1.1):             # 1位の前の溜め
    t = tt(d); n = noise(d); hi = n - lp_fast(n, 3)
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / d) ** 2) / SR)
    env = (t / d) ** 2.2
    return ((hi * 0.5 + tone * 0.25) * env).astype(np.float32)

SFX = {'boom': (boom, 0.38), 'rank': (impact, 0.5), 'pop': (pop, 0.7), 'fire': (cannon, 0.5), 'hit': (explosion, 0.5), 'ping': (ping, 0.8)}


def add(buf, t, x, gain):
    s = int(t * SR); e = min(len(buf), s + len(x))
    if 0 <= s < e: buf[s:e] += x[:e - s] * gain


def main():
    with wave.open(os.path.join(OUT, 'narration.wav')) as w:
        voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    n = len(voice)
    music = bgm.generate(n / SR)[:n]
    with wave.open(os.path.join(OUT, 'bgm.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((music * 32767).astype(np.int16).tobytes())

    # 効果音トラック
    fx = np.zeros(n, dtype=np.float32)
    cache = {}
    for i, sc in enumerate(tl['scenes']):
        if i > 0:
            add(fx, sc['start'] - 0.12, whoosh(), 0.55)
        for c in sc['cues']:
            k = c['sfx']
            if k in SFX:
                fn, gn = SFX[k]
                if k not in cache: cache[k] = fn()
                add(fx, c['start'] + SFX_OFF.get(k, 0) - (0.02 if k == 'rank' else 0), cache[k], gn)
    rank1 = next(sc for sc in tl['scenes'] if sc['id'] == 'torpedo')
    r1 = rank1['cues'][0]['start']
    rs = riser(); add(fx, r1 - len(rs) / SR, rs, 0.5)

    # BGM のダッキング(ナレーションの包絡から)
    hop = SR // 20
    rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(rms)
    for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0.0) * 0.9)
    env = np.pad(np.repeat(env, hop), (0, n - len(env) * hop))
    speech = np.clip(env / 0.08, 0, 1)
    gain = 0.42 - (0.42 - 0.16) * speech
    # 1位の直前は BGM を止める
    tsec = np.arange(n) / SR
    gate = np.ones(n, dtype=np.float32)
    gate[(tsec > rank1['start'] - 0.15) & (tsec < r1)] = 0.0
    gain = gain * gate
    k = SR // 12; gain = np.convolve(gain, np.ones(k) / k, mode='same')

    mixed = voice * 1.0 + music * gain + fx * 0.55
    mixed /= max(1.0, np.max(np.abs(mixed)) / 0.95)
    mix_wav = os.path.join(OUT, 'mix.wav')
    with wave.open(mix_wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mixed * 32767).astype(np.int16).tobytes())

    src = os.path.join(OUT, 'video_silent.mp4'); dst = os.path.join(OUT, 'kyugun_sugoi_short.mp4')
    # 2パスの loudnorm(1回目で計測し、2回目は線形にゲインだけ合わせる)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', mix_wav, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    j = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    ln = ('loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:'
          'measured_thresh={input_thresh}:offset={target_offset}:linear=true').format(**j) + ',volume=1dB'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', mix_wav, '-c:v', 'copy',
                    '-af', ln, '-ac', '2', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', '-movflags', '+faststart', dst], check=True)
    os.remove(mix_wav)
    print('wrote', dst)


if __name__ == '__main__':
    main()
