"""オリジナルBGM・効果音ジェネレータ（著作権フリー：すべてこのコードで合成）
和風の陽音階(D E G A B)で、琴っぽいはじき音＋太鼓＋拍子木のループを作る。
"""
import numpy as np

SR = 48000
BPM = 104
BEAT = 60 / BPM
E8 = BEAT / 2

def hz(midi): return 440.0 * 2 ** ((midi - 69) / 12)

def env_exp(n, decay):
    t = np.arange(n) / SR
    return np.exp(-t * decay)

def koto(f, dur=1.4, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for k in range(1, 8):
        y += (1 / k ** 1.3) * np.sin(2 * np.pi * f * k * (1 + 0.0007 * k * k) * t) * np.exp(-t * (2.5 + 1.6 * k))
    att = np.minimum(1, t / 0.003)
    # はじいた瞬間の爪の音
    y += 0.25 * np.random.default_rng(int(f)).standard_normal(n) * np.exp(-t * 300)
    return y * att * vel

def bass(f, dur=0.9, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return y * np.exp(-t * 3.5) * np.minimum(1, t / 0.005) * vel

def taiko(vel=1.0, big=False):
    dur = 0.9 if big else 0.5
    n = int(dur * SR); t = np.arange(n) / SR
    f = (55 if big else 75) + 90 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t * (4 if big else 8))
    y += 0.3 * np.random.default_rng(1).standard_normal(n) * np.exp(-t * 60)
    return y * vel

def click(vel=1.0):  # 拍子木っぽい「カッ」
    n = int(0.08 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 90) + 0.5 * np.sin(2 * np.pi * 3100 * t) * np.exp(-t * 140)
    return y * vel

def shaker(vel=1.0):
    n = int(0.06 * SR); t = np.arange(n) / SR
    noise = np.random.default_rng(7).standard_normal(n)
    noise = np.diff(np.concatenate([[0], noise]))  # 高域寄りに
    return noise * np.exp(-t * 70) * vel

def put(buf, x, start):
    i = int(start * SR)
    if i >= len(buf): return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m]

# 陽音階 D4=62: D E G A B
SCALE = [62, 64, 67, 69, 71, 74, 76, 79, 81]
# 2小節モチーフ（8分音符単位、Noneは休符、数値はSCALEの番号）
MOTIF_A = [4, None, 3, 4, 5, None, 4, 3,   2, None, 3, None, 1, 2, 0, None]
MOTIF_B = [5, None, 6, 5, 4, None, 3, 4,   5, 6, 7, None, 6, None, 5, None]
MOTIF_C = [3, None, 2, 3, 4, None, 2, 1,   0, None, 1, 2, 0, None, None, None]
ROOTS = [50, 55, 57, 50]  # D G A D（ベース、1小節ずつ）

def make_bgm(total):
    L = int(total * SR) + SR
    mel = np.zeros(L); bas = np.zeros(L); drm = np.zeros(L); pad = np.zeros(L)
    bar = BEAT * 4
    nbars = int(total / bar) + 2
    phrases = [MOTIF_A, MOTIF_B, MOTIF_A, MOTIF_C]
    for b in range(nbars):
        t0 = b * bar
        root = ROOTS[b % 4]
        # ベース：1拍目・3拍目裏
        put(bas, bass(hz(root), vel=0.9), t0)
        put(bas, bass(hz(root), vel=0.6), t0 + BEAT * 2.5)
        put(bas, bass(hz(root + 7), vel=0.5), t0 + BEAT * 3)
        # 太鼓・拍子木・シェイカー
        put(drm, taiko(0.9), t0)
        put(drm, taiko(0.55), t0 + BEAT * 2)
        put(drm, taiko(0.4), t0 + BEAT * 2.5)
        for k in range(4):
            put(drm, click(0.18 if k % 2 else 0.1), t0 + BEAT * k + E8)
        for k in range(8):
            put(drm, shaker(0.06 if k % 2 else 0.035), t0 + E8 * k)
        # メロディ（最初の2小節はリズムだけで入る）
        if b >= 2:
            ph = phrases[((b - 2) // 2) % 4]
            half = (b - 2) % 2
            for k in range(8):
                deg = ph[half * 8 + k]
                if deg is not None:
                    put(mel, koto(hz(SCALE[deg]), vel=0.55), t0 + E8 * k)
                    if k == 0:  # 1拍目はオクターブ下を重ねて厚く
                        put(mel, koto(hz(SCALE[deg] - 12), vel=0.25), t0)
        # 薄いパッド（根音＋5度）
        n = int(bar * SR); t = np.arange(n) / SR
        p = (np.sin(2 * np.pi * hz(root + 12) * t) + 0.6 * np.sin(2 * np.pi * hz(root + 19) * t))
        p *= np.minimum(1, t / 0.3) * np.minimum(1, (bar - t) / 0.3) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.5 * t))
        put(pad, p * 0.06, t0)
    mix_l = 0.9 * mel + 0.8 * bas + drm + pad
    mix_r = 0.7 * mel + 0.8 * bas + drm + pad
    # 簡易ステレオ：メロディを少しずらす
    d = int(0.012 * SR)
    mix_r[d:] += 0.25 * mel[:-d]
    out = np.stack([mix_l, mix_r], axis=1)[: int(total * SR)]
    # フェードイン・アウト
    n = len(out); t = np.arange(n) / SR
    fade = np.minimum(1, t / 0.4) * np.minimum(1, (total - t) / 1.8)
    out *= fade[:, None]
    return out / np.max(np.abs(out)) * 0.5

# ---------------- 効果音 ----------------
def se_don():
    y = taiko(1.0, big=True)
    return y

def se_kira():
    y = np.zeros(int(0.9 * SR))
    for i, m in enumerate([86, 90, 93, 98]):
        n = int(0.7 * SR); t = np.arange(n) / SR
        tone = (np.sin(2 * np.pi * hz(m) * t) + 0.3 * np.sin(2 * np.pi * hz(m) * 2.76 * t)) * np.exp(-t * 6)
        put(y, tone * 0.35, i * 0.05)
    return y

def se_coin():
    y = np.zeros(int(1.0 * SR))
    for i in range(5):
        n = int(0.35 * SR); t = np.arange(n) / SR
        f = 2400 + 300 * (i % 3)
        tone = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t)) * np.exp(-t * 18)
        put(y, tone * 0.25, i * 0.09)
    return y

def se_stamp():
    y = taiko(1.0, big=True) * 1.2
    n = int(0.25 * SR); t = np.arange(n) / SR
    crunch = np.random.default_rng(3).standard_normal(n) * np.exp(-t * 25) * 0.5
    put(y, crunch, 0)
    return y

def se_pop():
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 500 + 1400 * t / 0.12
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30) * 0.4

SE = dict(don=se_don, kira=se_kira, coin=se_coin, stamp=se_stamp, pop=se_pop)

def make_se(total, events):
    buf = np.zeros(int(total * SR) + SR)
    for t, name in events:
        put(buf, SE[name](), max(0, t))
    buf = buf[: int(total * SR)]
    return np.stack([buf, buf], axis=1) * 0.8

def write_wav(path, data):
    import wave
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(data.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
