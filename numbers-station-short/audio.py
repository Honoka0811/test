"""BGM・効果音を合成し、ナレーションとミックスする（素材はすべてコードで生成＝著作権フリー）。"""
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 48000
rng = np.random.default_rng(76)


def db(x):
    return 10 ** (x / 20)


def band(x, lo, hi, order=4):
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def lowpass(x, f, order=4):
    return sosfilt(butter(order, f, fs=SR, output="sos"), x)


def smooth_noise(n, rate_hz):
    """ゆっくり揺らぐ 0..1 のランダム曲線（短波のフェージング用）"""
    k = max(2, int(n / SR * rate_hz) + 2)
    pts = rng.random(k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)


def reverb(x, sec=2.2, wet=0.35):
    n = int(sec * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir = lowpass(ir, 5000)
    ir /= np.abs(ir).sum() ** 0.5 * 8
    return x * (1 - wet) + fftconvolve(x, ir)[: len(x)] * wet


def env_ar(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1) * np.exp(-t / r)


def put(buf, sig, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


# ---------- 素材 ----------
def static_bed(n):
    w = rng.standard_normal(n)
    s = band(w, 250, 3500) * (0.35 + 0.65 * smooth_noise(n, 3)) ** 2
    crackle = (rng.random(n) > 0.9993) * rng.standard_normal(n) * 3
    return s + lowpass(crackle, 4000)


def static_burst(dur=0.35):
    n = int(dur * SR)
    s = band(rng.standard_normal(n), 400, 6000)
    s *= np.sin(np.linspace(0, np.pi, n)) ** 0.5
    # ビットクラッシュ風のグリッチ
    hold = 40
    s = np.repeat(s[::hold], hold)[:n]
    return s


def drone(n):
    t = np.arange(n) / SR
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)
    x = np.zeros(n)
    for f, a in [(55, 1), (55.4, 0.8), (82.4, 0.45), (110.2, 0.3), (130.8, 0.18)]:  # A + 短3度で不穏に
        for h in range(1, 6):
            x += a / h ** 1.4 * np.sin(2 * np.pi * f * h * t + rng.random() * 6)
    return lowpass(x, 900) * lfo


def heartbeat(n, start, end, bpm0, bpm1):
    out = np.zeros(n)
    t = start
    beat = None
    m = int(0.35 * SR)
    tt = np.arange(m) / SR
    thump = np.sin(2 * np.pi * (48 + 40 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14)
    while t < end:
        bpm = bpm0 + (bpm1 - bpm0) * (t - start) / max(end - start, 1e-3)
        put(out, thump, t, 1.0)
        put(out, thump, t + 0.22, 0.6)
        t += 60 / bpm
    return out


def music_box_note(freq, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.01 * t)
         + 0.12 * np.sin(2 * np.pi * freq * 3.98 * t))
    return x * env_ar(n, 0.003, 0.45)


def music_box(n, start, end, step=0.42):
    # A minor の不穏なオルゴール（オリジナル）
    A4 = 440.0
    semis = [0, 7, 3, 2, 0, 7, 3, -1, 0, 7, 5, 3, 2, 3, -1, -5]
    out = np.zeros(n)
    t, i = start, 0
    while t < end:
        f = A4 * 2 ** (semis[i % len(semis)] / 12)
        put(out, music_box_note(f), t)
        if i % 4 == 0:
            put(out, music_box_note(f / 2), t, 0.5)
        t += step
        i += 1
    return reverb(out, 2.5, 0.45)


def buzzer(dur):
    """UVB-76 風のブザー（約1秒鳴って休む、を繰り返す）"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = np.sign(np.sin(2 * np.pi * 118 * t)) * 0.6 + np.sin(2 * np.pi * 236 * t) * 0.4
    tone = band(tone, 80, 2500)
    gate = ((t % 1.5) < 1.0).astype(float)
    gate = np.convolve(gate, np.ones(400) / 400, mode="same")
    return tone * gate


def tick():
    n = int(0.03 * SR)
    return band(rng.standard_normal(n), 2000, 9000) * np.exp(-np.arange(n) / SR * 200)


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 200 * 2 ** (t / dur * 3)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + band(rng.standard_normal(n), 500, 8000) * 0.6
    return s * (t / dur) ** 2


def impact(dur=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * (35 + 60 * np.exp(-t * 8)) * t) * np.exp(-t * 2.2)
    s += lowpass(rng.standard_normal(n), 1200) * np.exp(-t * 6) * 0.5
    return reverb(s, 3, 0.3)


# ---------- ミックス ----------
def normalize(x, peak_db):
    p = np.abs(x).max() + 1e-9
    return x / p * db(peak_db)


def build_mix(total, scenes, voices, events):
    """scenes: start/end/vstart を持つ dict 列, voices: [np.array], events: [(t, kind)]"""
    n = int(total * SR)
    idx = {s["id"]: s for s in scenes}
    vo = np.zeros(n)
    for s, v in zip(scenes, voices):
        put(vo, v, s["vstart"])

    bgm = np.zeros(n)
    bgm += normalize(static_bed(n), -30)
    bgm += normalize(drone(n), -21)

    hb_start = idx["title"]["start"]
    hb_end = idx["hidden"]["start"]
    bgm += normalize(heartbeat(n, hb_start, hb_end, 62, 96), -18)

    mb = music_box(n, idx["title"]["start"], idx["uvb"]["start"] - 0.2)
    mb += music_box(n, idx["nk"]["start"], idx["hidden"]["start"] - 1.6)
    bgm += normalize(mb, -21)

    u = idx["uvb"]
    bz = buzzer(u["end"] - u["start"] + 0.6)
    put(bgm, normalize(bz, -19), u["start"])

    # クライマックス：ライザー → 衝撃音 → 余韻の静けさ
    h = idx["hidden"]
    put(bgm, normalize(riser(1.6), -14), h["start"] - 1.6)
    put(bgm, normalize(impact(), -8), h["start"])
    bgm += normalize(heartbeat(n, h["start"] + 0.4, total - 0.6, 54, 54), -20)

    sfx = np.zeros(n)
    for t, kind in events:
        if kind == "glitch":
            put(sfx, static_burst(), t, db(-13))
        elif kind == "tick":
            put(sfx, tick(), t, db(-20))
        elif kind == "stamp":
            put(sfx, impact(0.6), t, db(-14))
    # ループ用：終わりは砂嵐が膨らんで冒頭の砂嵐へつながる
    tail = static_burst(1.0) * np.linspace(0, 1, SR) ** 2
    put(sfx, tail, total - 1.0, db(-12))
    put(sfx, static_burst(0.5), 0, db(-12))

    # ナレーション中は BGM を下げる（ダッキング）
    env = np.convolve(np.abs(vo), np.ones(int(0.08 * SR)) / int(0.08 * SR), mode="same")
    duck = 1 - 0.55 * np.clip(env / (np.abs(vo).max() * 0.08 + 1e-9), 0, 1)
    duck = np.convolve(duck, np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")

    mix = vo + (bgm * duck + sfx) * 0.9
    mix = np.tanh(mix / (np.abs(mix).max() + 1e-9) * 1.4) / np.tanh(1.4) * 0.95
    return mix.astype(np.float32), vo.astype(np.float32)
