# -*- coding: utf-8 -*-
"""効果音を numpy だけで合成する(外部音源なし・権利フリー)。すべて 48kHz ステレオ float32 を返す。"""
import numpy as np

SR = 48000


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _stereo(x, pan=0.0):
    """pan: -1(左)〜 +1(右)。等パワーパン。"""
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1).astype(np.float32)


def _bandpass_noise(n, f_lo, f_hi, rng):
    """FFT マスクで帯域制限したノイズ。"""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    mask = np.exp(-0.5 * ((np.log(np.maximum(f, 1)) - np.log(np.sqrt(f_lo * f_hi))) / (np.log(f_hi / f_lo) / 2.2)) ** 2)
    x = np.fft.irfft(spec * mask, n)
    return x / (np.max(np.abs(x)) + 1e-9)


def whoosh(dur=0.45, f0=500, f1=5000, pan_from=-0.6, pan_to=0.6, seed=1):
    """場面転換のシュッという音。帯域が上がりながら左右に流れる。"""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / n
    lo = _bandpass_noise(n, f0 * 0.6, f0 * 1.8, rng)
    hi = _bandpass_noise(n, f1 * 0.6, f1 * 1.6, rng)
    x = lo * (1 - t) + hi * t
    env = np.sin(np.pi * t) ** 1.6
    x = x * env
    pan = pan_from + (pan_to - pan_from) * t
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1).astype(np.float32)


def pop(f=660, dur=0.12, pan=0.0):
    """項目が出るときの軽いポップ。"""
    t = _t(dur)
    fr = f * (1 + 0.9 * np.exp(-t / 0.012))
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.035)
    return _stereo(x, pan)


def tick(f=2400, dur=0.03, pan=0.0):
    """カウンター用の短いクリック。"""
    t = _t(dur)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.004)
    return _stereo(x, pan)


def impact(dur=1.4, f0=110, f_end=38, seed=2):
    """数字が決まる瞬間のドン(サブベース + アタックノイズ)。"""
    rng = np.random.default_rng(seed)
    t = _t(dur)
    f = f_end + (f0 - f_end) * np.exp(-t / 0.07)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.38)
    body = np.tanh(body * 1.6) / np.tanh(1.6)
    n = len(t)
    click = _bandpass_noise(n, 900, 6000, rng) * np.exp(-t / 0.018)
    rumble = _bandpass_noise(n, 40, 160, rng) * np.exp(-t / 0.5) * 0.35
    x = body + 0.5 * click + rumble
    x = x / np.max(np.abs(x))
    l = x + 0.08 * np.roll(x, 211)
    r = x + 0.08 * np.roll(x, 307)
    return np.stack([l, r], axis=1).astype(np.float32)


def riser(dur=1.6, f0=180, f1=1400, seed=3):
    """リビール前の上昇音(ノイズ + ピッチ上昇トーン)。最後で切る。"""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / n
    f = f0 * (f1 / f0) ** (t ** 1.4)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    noise = _bandpass_noise(n, 1500, 9000, rng)
    env = t ** 2.2
    x = (0.5 * tone + 0.8 * noise) * env
    trem = 1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * (6 + 18 * t) * t * dur))
    x = x * trem
    x[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))
    x = x / np.max(np.abs(x))
    return np.stack([x * (0.9 + 0.1 * np.sin(40 * t)), x * (0.9 - 0.1 * np.sin(40 * t))], axis=1).astype(np.float32)


def ding(f=1318.5, dur=1.2, pan=0.0):
    """正解・強調のベル。"""
    t = _t(dur)
    x = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t / d)
            for h, a, d in ((1, 1.0, 0.35), (2.76, 0.35, 0.18), (5.4, 0.18, 0.09), (2.0, 0.25, 0.25)))
    x *= np.minimum(1, t / 0.002)
    return _stereo(x / np.max(np.abs(x)), pan)


def sparkle(dur=0.9, seed=4):
    """キラキラ(高音の粒が散る)。"""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros((n, 2), dtype=np.float32)
    for i in range(14):
        f = rng.choice([2093, 2637, 3136, 3951, 4186, 5274])
        st = int(rng.uniform(0, dur * 0.6) * SR)
        g = ding(f, 0.35, pan=rng.uniform(-0.8, 0.8)) * rng.uniform(0.3, 0.8)
        e = min(n, st + len(g))
        out[st:e] += g[:e - st]
    return out / (np.max(np.abs(out)) + 1e-9)


def sub_drop(dur=0.9, f0=160, f1=30):
    """落下するサブベース(スケールが一気に変わるとき)。"""
    t = _t(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.22)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.01) * np.exp(-t / 0.45)
    return _stereo(x, 0.0)


def blip_up(dur=0.18, f0=520, f1=1040, pan=0.0):
    """短い上昇ブリップ(「増えた」感)。"""
    t = _t(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.3 * np.sign(np.sin(ph))) * np.exp(-t / 0.09) * np.minimum(1, t / 0.003)
    return _stereo(x / np.max(np.abs(x)), pan)


def heartbeat(dur=0.5):
    """低い二連打(緊張感)。"""
    n = int(dur * SR)
    out = np.zeros(n)
    for st, g in ((0.0, 1.0), (0.16, 0.7)):
        t = _t(0.25)
        f = 45 + 40 * np.exp(-t / 0.03)
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.07) * g
        s = int(st * SR)
        out[s:s + len(b)] += b[:n - s]
    return _stereo(out / np.max(np.abs(out)), 0.0)


def hit(dur=0.45, f0=180, f_end=60, seed=5):
    """数字が出る瞬間の短いパンチ(impact より軽い)。"""
    rng = np.random.default_rng(seed)
    t = _t(dur)
    f = f_end + (f0 - f_end) * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)
    click = _bandpass_noise(len(t), 1500, 7000, rng) * np.exp(-t / 0.012)
    x = body + 0.45 * click
    return _stereo(x / np.max(np.abs(x)), 0.0)


def buzz(dur=0.28, f=98):
    """「足りない」の短いブザー(低い矩形波 2 音)。"""
    t = _t(dur)
    x = np.zeros_like(t)
    for ff in (f, f * 1.06):
        ph = 2 * np.pi * ff * t
        x += sum(np.sin(ph * h) / h for h in (1, 3, 5, 7))
    env = np.minimum(1, t / 0.005) * np.minimum(1, (dur - t) / 0.03)
    gate = np.where((t > 0.11) & (t < 0.15), 0.0, 1.0)
    x = x * env * gate
    return _stereo(x / np.max(np.abs(x)), 0.0)


def place(buf, t, sig, gain=1.0):
    """buf(N×2)の時刻 t 秒に sig を加算する。"""
    s = int(round(t * SR))
    if s < 0:
        sig = sig[-s:]
        s = 0
    e = min(len(buf), s + len(sig))
    if e > s:
        buf[s:e] += sig[:e - s] * gain
