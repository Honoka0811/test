"""BGM（オリジナル合成）・効果音・ナレーションをミックスして mix.wav を作る。"""
import json, sys, wave, pathlib
import numpy as np

B = pathlib.Path(sys.argv[1])
SR = 48000
cues = json.loads((B / "cues.json").read_text())
tl = json.loads((B / "voice" / "timeline.json").read_text())
TOTAL = cues["total"] + 0.3
N = int(TOTAL * SR)
rng = np.random.default_rng(7)


def tarr(d):
    return np.arange(int(d * SR)) / SR


def add(buf, x, t):
    i = int(t * SR)
    if i >= len(buf):
        return
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += x


def lp(x, a):  # 1次ローパス（a: 0〜1、小さいほど暗い）
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def lp_fast(x, cutoff):
    # FFT による簡易ローパス
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def hp_fast(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 - 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def saw(f, t, detune=0.0):
    out = 0
    for d in (-detune, 0, detune) if detune else (0,):
        ph = (f * (1 + d) * t) % 1
        out = out + (2 * ph - 1)
    return out / (3 if detune else 1)


# ---------- 楽器 ----------
def kick():
    t = tarr(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) * 1.0 + np.sin(ph * 2) * np.exp(-t * 40) * 0.2


def clap():
    t = tarr(0.3)
    n = hp_fast(rng.standard_normal(len(t)), 900)
    env = np.exp(-t * 18)
    for k in (0.011, 0.022):  # クラップの多重アタック
        env += 0.6 * np.exp(-np.maximum(t - k, 0) * 60) * (t >= k)
    return n * env * 0.32


def hat(open_=False):
    t = tarr(0.25 if open_ else 0.06)
    n = hp_fast(rng.standard_normal(len(t)), 7000)
    return n * np.exp(-t * (14 if open_ else 70)) * 0.13


def bass_note(n, d):
    t = tarr(d)
    f = midi(n)
    x = 0.7 * np.sin(2 * np.pi * f * t) + 0.35 * lp_fast(saw(f, t), 400)
    env = np.minimum(1, t * 200) * np.exp(-t * 2.2)
    return x * env * 0.42


def pluck(n, d=0.32):
    t = tarr(d)
    f = midi(n)
    sq = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + saw(f, t, 0.006) * 0.5
    x = lp_fast(sq, 2600) * np.exp(-t * 11)
    return x * 0.09


def pad_chord(notes, d):
    t = tarr(d)
    x = sum(saw(midi(n), t, 0.004) for n in notes)
    x = lp_fast(x, 1200)
    env = np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 0.3)
    return x * env * 0.035


# ---------- BGM ----------
BPM = 124
beat = 60 / BPM
bar = beat * 4
T0 = 0.6  # 最初のインパクトから拍を始める
# Am - F - C - G（ルート, コードトーン）
prog = [(45, [57, 60, 64, 69]), (41, [53, 57, 60, 65]), (48, [55, 60, 64, 67]), (43, [55, 59, 62, 67])]

drums = np.zeros(N); bassb = np.zeros(N); synth = np.zeros(N); pad = np.zeros(N)
K, C, H, HO = kick(), clap(), hat(), hat(True)
rice_start = next(s for s in tl["scenes"] if s["id"] == "rice")["start"] + 0.3
rice_hit = cues["reveal"]["rice"]
end_hit = cues["total"] - 1.2

nbars = int((TOTAL - T0) / bar) + 1
for b in range(nbars):
    root, chord = prog[b % 4]
    tb = T0 + b * bar
    add(pad, pad_chord(chord, bar + 0.05), tb)
    for s in range(16):  # 16分
        ts = tb + s * beat / 4
        if ts >= end_hit:
            break
        drop = rice_start <= ts < rice_hit
        if not drop:
            if s % 4 == 0:
                add(drums, K, ts)
            if s in (4, 12):
                add(drums, C, ts)
            if s % 2 == 0:
                add(drums, H * (1.0 if s % 4 == 2 else 0.6), ts)
            if s in (10, 15) or (ts > rice_hit and s % 2 == 1):
                add(drums, (HO if s == 10 else H * 0.5), ts)
            if s % 2 == 0 or s in (3, 11):
                n = root if s % 8 else root  # オクターブ跳躍で躍動感
                add(bassb, bass_note(n + (12 if s in (6, 14) else 0), beat / 2 * 0.95), ts)
        # アルペジオ（ドロップ中も鳴らして緊張感を保つ）
        arp = chord[[0, 2, 1, 3, 2, 1, 3, 2][s % 8]] + 12
        add(synth, pluck(arp) * (0.6 if drop else 1.0), ts)

# サイドチェイン風のポンピング（キックに合わせてベース・パッドを下げる）
pump = np.ones(N)
tt = np.arange(N) / SR
ph = ((tt - T0) % beat) / beat
pump = 0.55 + 0.45 * np.minimum(1, ph / 0.45)
bgm = drums + (bassb + pad) * pump + synth
# 3連ディレイでシンセに広がり
d = int(beat * 0.75 * SR)
synth_echo = np.zeros(N); synth_echo[d:] = synth[:-d] * 0.35
bgm += synth_echo * pump

# 終わり：ラストのコードを伸ばしてフェードアウト
add(bgm, pad_chord([57, 60, 64, 69, 72], 1.6) * 3, end_hit)
add(bgm, kick() * 1.0, end_hit)
fade = np.ones(N)
fi = int(end_hit * SR)
fade[fi:] = np.linspace(1, 0, N - fi) ** 1.5
bgm *= fade

# ---------- 効果音 ----------
def whoosh(d=0.35):
    t = tarr(d)
    n = rng.standard_normal(len(t))
    x = np.zeros_like(n)
    # 時間で変わるバンドパス（ブロックごとにFFT）
    blk = 1024
    for i in range(0, len(n), blk):
        seg = n[i:i + blk]
        c = 500 + 5000 * (i / len(n))
        X = np.fft.rfft(seg); f = np.fft.rfftfreq(len(seg), 1 / SR)
        X *= np.exp(-((f - c) / (c * 0.6)) ** 2)
        x[i:i + blk] = np.fft.irfft(X, len(seg))
    env = np.sin(np.pi * t / d) ** 2
    return x * env * 0.5


def coin():
    t = tarr(0.5)
    x = np.sin(2 * np.pi * 1975 * t) * (t < 0.07) + np.sin(2 * np.pi * 2637 * t) * (t >= 0.07)
    return x * np.exp(-np.maximum(t - 0.07, 0) * 7) * 0.16


def stamp():
    t = tarr(0.35)
    body = np.sin(2 * np.pi * (90 + 120 * np.exp(-t * 40)) * t) * np.exp(-t * 18)
    n = lp_fast(rng.standard_normal(len(t)), 2500) * np.exp(-t * 35)
    return (body * 0.6 + n * 0.5) * 0.7


def impact():
    t = tarr(1.6)
    f = 35 + 80 * np.exp(-t * 10)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.5)
    n = lp_fast(rng.standard_normal(len(t)), 1800) * np.exp(-t * 6)
    return (boom * 0.9 + n * 0.35) * 0.8


def hit():
    t = tarr(0.5)
    f = 60 + 150 * np.exp(-t * 30)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.6
            + hp_fast(rng.standard_normal(len(t)), 3000) * np.exp(-t * 25) * 0.25)


def pop():
    t = tarr(0.12)
    f = 400 + 900 * t / 0.12
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30) * 0.25


def tick():
    t = tarr(0.05)
    return np.sin(2 * np.pi * 1600 * t) * np.exp(-t * 90) * 0.12


def riser(d):
    t = tarr(d)
    n = rng.standard_normal(len(t))
    x = np.zeros_like(n); blk = 1024
    for i in range(0, len(n), blk):
        seg = n[i:i + blk]
        c = 300 + 6000 * (i / len(n)) ** 2
        X = np.fft.rfft(seg); f = np.fft.rfftfreq(len(seg), 1 / SR)
        X *= np.exp(-((f - c) / (c * 0.4)) ** 2)
        x[i:i + blk] = np.fft.irfft(X, len(seg))
    tone = np.sin(2 * np.pi * np.cumsum(200 + 800 * (t / d) ** 2) / SR) * 0.15
    return (x * 0.6 + tone) * (t / d) ** 2 * 0.6


sfx = np.zeros(N)
gen = {"whoosh": whoosh, "coin": coin, "stamp": stamp, "impact": impact, "hit": hit, "pop": pop, "tick": tick}
for e in cues["sfx"]:
    if e["k"] == "riser":
        add(sfx, riser(e["until"] - e["t"]), e["t"])
    else:
        add(sfx, gen[e["k"]](), max(0, e["t"]))

# ---------- ナレーション ----------
voice = np.zeros(N)
for s in tl["scenes"]:
    with wave.open(str(B / "voice" / f"{s['id']}.wav")) as w:
        assert w.getframerate() == SR
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    add(voice, x, s["start"])

# 声がある間はBGMを下げる（ダッキング）
env = np.abs(voice)
win = int(0.05 * SR)
env = np.convolve(env, np.ones(win) / win, mode="same")
active = (env > 0.01).astype(float)
sm = int(0.15 * SR)
active = np.convolve(active, np.ones(sm) / sm, mode="same")
duck = 1 - 0.45 * np.clip(active, 0, 1)

bgm = bgm / (np.max(np.abs(bgm)) + 1e-9)
mix = bgm * 0.30 * duck + sfx * 0.55 + voice * 1.35
mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # ソフトリミッタ
mix /= max(1.0, np.max(np.abs(mix)) / 0.97)

out = (np.stack([mix, mix], axis=1) * 32767).astype(np.int16)
with wave.open(str(B / "mix.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(out.tobytes())
bgm_only = (np.stack([bgm * 0.5] * 2, axis=1) * 32767).astype(np.int16)
with wave.open(str(B / "bgm.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(bgm_only.tobytes())
print("mix.wav", round(N / SR, 2), "s")
