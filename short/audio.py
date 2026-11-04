# BGM(オリジナル合成のトラップ/ローファイ系ビート)と効果音を作り、ナレーションとミックスする
import json, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)
tl = json.load(open("build/timeline.json"))
TOTAL = tl["total"]
N = int(TOTAL * SR) + SR


def read_wav(p):
    with wave.open(p) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
        assert w.getframerate() == SR
    return a


def add(buf, sig, t):
    i = int(t * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig


def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(t / a, 1) * np.exp(-t / d)
    return e


def note(m):
    return 440 * 2 ** ((m - 69) / 12)


# ---------- 楽器 ----------
def kick808(f0=note(33), dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 + (f0 * 3.5) * np.exp(-t * 35)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t / 0.45)
    s = np.tanh(s * 2.2) * 0.9
    click = rng.standard_normal(n) * np.exp(-t / 0.003) * 0.3
    return s + click


def clap():
    n = int(0.35 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    e = np.zeros(n)
    for off in (0, 0.011, 0.022):
        k = int(off * SR); e[k:] += np.exp(-(t[: n - k]) / (0.012 if off < 0.02 else 0.12))
    # 簡易バンドパス(差分)
    s = np.diff(nz, prepend=0) * e
    return s * 0.35


def hat(open_=False):
    n = int((0.25 if open_ else 0.05) * SR); t = np.arange(n) / SR
    s = np.diff(np.diff(rng.standard_normal(n), prepend=0), prepend=0)
    return s * np.exp(-t / (0.08 if open_ else 0.012)) * 0.08


def pluck(m, dur=0.5, vol=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    f = note(m)
    s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.05)
         + 0.25 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.03))
    return s * env(n, 0.003, 0.18) * vol


def pad(ms, dur, vol=0.035):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for m in ms:
        for det in (-0.12, 0, 0.12):
            f = note(m + det)
            s += 2 * ((f * t + rng.random()) % 1) - 1  # ノコギリ
    # 1次ローパス
    a = 0.04
    out = np.zeros(n); y = 0
    # ベクトル化された指数平滑(IIR)
    from scipy.signal import lfilter  # noqa
    out = lfilter([a], [1, a - 1], s)
    e = np.minimum(t / 0.25, 1) * np.minimum((dur - t) / 0.3, 1)
    return out * e * vol / len(ms)


# ---------- BGM ----------
try:
    import scipy  # noqa
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "scipy"])

BPM = 140
beat = 60 / BPM
bar = beat * 4
bgm = np.zeros(N)
# Am - F - C - G (各1小節)
prog = [(57, [57, 60, 64], 45), (53, [53, 57, 60], 41), (48, [52, 55, 60], 48), (55, [55, 59, 62], 43)]
drop_t = tl["scenes"][1]["start"]  # 1つ目の習慣でドロップ
outro = tl["scenes"][-1]

bars = int(TOTAL / bar) + 2
for b in range(bars):
    t0 = b * bar
    root, chord, bass = prog[b % 4]
    full = t0 >= drop_t - 0.01
    add(bgm, pad([m + 12 for m in chord], bar + 0.3), t0)
    # アルペジオ(16分)
    arp = chord + [chord[0] + 12, chord[1] + 12, chord[2], chord[1] + 12, chord[0] + 12]
    for i in range(8):
        add(bgm, pluck(arp[i % len(arp)] + 12, vol=0.08 if full else 0.06), t0 + i * beat / 2)
    if not full:
        continue
    # 808 キック+ベース
    for k, pos in enumerate([0, 1.5, 2.75] if b % 2 == 0 else [0, 1.5, 2.5, 3.5]):
        add(bgm, kick808(note(bass - 12), 0.6 if k else 0.9) * 0.55, t0 + pos * beat)
    # クラップ(3拍目)
    add(bgm, clap(), t0 + 2 * beat)
    # ハイハット 8分 + ロール
    for i in range(8):
        add(bgm, hat(), t0 + i * beat / 2)
    if b % 2 == 1:
        for j in range(6):  # 3連ロール
            add(bgm, hat() * 0.8, t0 + 3 * beat + j * beat / 6)
    if b % 4 == 3:
        add(bgm, hat(True), t0 + 3.5 * beat)

# ドロップ前のライザー
n = int(bar * SR); t = np.arange(n) / SR
riser = rng.standard_normal(n) * (t / t[-1]) ** 2 * 0.12
add(bgm, riser, drop_t - bar)


# ---------- 効果音 ----------
sfx = np.zeros(N)


def whoosh(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    from scipy.signal import lfilter
    nz = rng.standard_normal(n)
    a = 0.02 + 0.25 * np.sin(np.pi * t / dur)  # フィルタの開閉
    out = np.zeros(n); y = 0.0
    for i in range(n):
        y += a[i] * (nz[i] - y); out[i] = y
    return out * np.sin(np.pi * t / dur) ** 2 * 0.5


def impact():
    n = int(1.2 * SR); t = np.arange(n) / SR
    f = 50 + 120 * np.exp(-t * 20)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.5)
    nz = rng.standard_normal(n) * np.exp(-t / 0.08) * 0.3
    return np.tanh((s + nz) * 2) * 0.6


def coin():  # チャリーン
    n = int(0.9 * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for f, d, start in ((2637, 0.25, 0), (3520, 0.5, 0.08)):
        k = int(start * SR); tt = t[: n - k]
        s[k:] += (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt / d)
    return s * 0.16


def pop():
    n = int(0.08 * SR); t = np.arange(n) / SR
    f = 900 - 500 * t / t[-1]
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.02) * 0.18


add(sfx, impact(), tl["scenes"][0]["lines"][0]["start"] - 0.05)
add(sfx, impact() * 0.8, tl["scenes"][0]["lines"][1]["start"] - 0.05)
for sc in tl["scenes"][1:]:
    add(sfx, whoosh(), sc["start"] - 0.25)
    if sc["kind"] == "habit":
        add(sfx, coin(), sc["start"] + 0.15)
    for ln in sc["lines"][1:]:
        add(sfx, pop(), ln["start"] - 0.02)
add(sfx, coin(), outro["lines"][-1]["start"])


# ---------- ボイス & ミックス ----------
voice = np.zeros(N)
for sc in tl["scenes"]:
    for ln in sc["lines"]:
        add(voice, read_wav(ln["wav"]) * 1.0, ln["start"])

# ダッキング: 声がある所でBGMを下げる
from scipy.signal import lfilter
lvl = np.abs(voice)
win = int(0.03 * SR)
lvl = np.convolve(lvl, np.ones(win) / win, "same")
gate = (lvl > 0.01).astype(float)
a_dn, a_up = 1 / (0.05 * SR), 1 / (0.35 * SR)
g = np.zeros(N); y = 0.0
# 簡易エンベロープフォロワー(アタック速く/リリース遅く)を区間ごとに
g = lfilter([a_up], [1, a_up - 1], gate)
g = np.maximum(g, lfilter([a_dn], [1, a_dn - 1], gate) * 0.0)
duck = 1 - 0.55 * np.clip(g * 1.5, 0, 1)

mix = voice * 1.05 + bgm * 0.55 * duck + sfx * 0.9
# フェードアウト
fo = int(1.2 * SR); end = int(TOTAL * SR)
mix[end - fo:end] *= np.linspace(1, 0, fo); mix[end:] = 0
mix = mix[:end]
peak = np.max(np.abs(mix))
mix = np.tanh(mix / peak * 1.3) / np.tanh(1.3) * 0.95


def write(p, a):
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


write("build/mix.wav", mix)
write("build/bgm_only.wav", bgm[:end] / np.max(np.abs(bgm)) * 0.9)
print("ok", TOTAL)
