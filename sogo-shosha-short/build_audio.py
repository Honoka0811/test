"""VOICEVOX(四国めたん)でナレーションを合成し、自作BGMとミックスする。

前提: VOICEVOX ENGINE が http://127.0.0.1:50021 で起動していること。
出力: build/voice_XX.wav, build/timeline.json, build/audio.wav
"""
import io
import json
import os
import urllib.parse
import urllib.request
import wave

import numpy as np

from script import LINES

ENGINE = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
SPEAKER = 2  # 四国めたん (ノーマル)
SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
os.makedirs(OUT, exist_ok=True)

LEAD_IN = 0.45      # 冒頭の無音
GAP_LINE = 0.22     # 同一シーン内の行間
GAP_SCENE = 0.55    # シーン間
TAIL = 1.6          # 末尾の余韻


def post(path, params, body=None):
    url = f"{ENGINE}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def synth(text):
    q = json.loads(post("/audio_query", {"text": text, "speaker": SPEAKER}))
    q["speedScale"] = 1.18
    q["intonationScale"] = 1.25
    q["prePhonemeLength"] = 0.05
    q["postPhonemeLength"] = 0.05
    q["outputSamplingRate"] = SR
    q["outputStereo"] = False
    raw = post("/synthesis", {"speaker": SPEAKER}, q)
    with wave.open(io.BytesIO(raw)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0, q["kana"]


# ---------------------------------------------------------------- narration
clips = []
for i, (scene, text, _sub) in enumerate(LINES):
    pcm, kana = synth(text)
    clips.append(pcm)
    print(f"{i:02d} {len(pcm)/SR:5.2f}s {kana}")

timeline = []
t = LEAD_IN
for i, (scene, _text, sub) in enumerate(LINES):
    if i > 0:
        t += GAP_SCENE if LINES[i - 1][0] != scene else GAP_LINE
    dur = len(clips[i]) / SR
    timeline.append({"i": i, "scene": scene, "start": round(t, 3),
                     "end": round(t + dur, 3), "sub": sub})
    t += dur
total = t + TAIL

scene_starts = {}
for e in timeline:
    scene_starts.setdefault(e["scene"], e["start"])
# シーンは発話の少し前に切り替える
scene_cuts = {k: (0.0 if k == "intro" else round(v - 0.38, 3)) for k, v in scene_starts.items()}

N = int(total * SR)
voice = np.zeros(N, dtype=np.float32)
for e, c in zip(timeline, clips):
    s = int(e["start"] * SR)
    voice[s:s + len(c)] += c[: N - s]
voice /= max(1e-6, np.abs(voice).max()) / 0.89

# ---------------------------------------------------------------- BGM (自作シンセ)
rng = np.random.default_rng(7)
BPM = 124
BEAT = 60 / BPM
BAR = BEAT * 4


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a=0.005, d=0.2):
    tt = np.arange(n) / SR
    return np.minimum(tt / a, 1.0) * np.exp(-tt / d)


def add(buf, start, sig, gain=1.0, pan=0.0):
    s = int(start * SR)
    if s >= N:
        return
    sig = sig[: N - s]
    buf[s:s + len(sig), 0] += sig * gain * (1 - max(0, pan))
    buf[s:s + len(sig), 1] += sig * gain * (1 + min(0, pan))


def tone(freq, dur, kind="tri"):
    tt = np.arange(int(dur * SR)) / SR
    ph = 2 * np.pi * freq * tt
    if kind == "sine":
        return np.sin(ph)
    if kind == "tri":
        return (np.sin(ph) - np.sin(3 * ph) / 9 + np.sin(5 * ph) / 25) * 0.9
    # soft saw
    return sum(np.sin(k * ph) / k for k in range(1, 7)) * 0.55


def kick():
    n = int(0.28 * SR)
    tt = np.arange(n) / SR
    f = 48 + 110 * np.exp(-tt / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.11)


def hat(d=0.03):
    n = int(0.09 * SR)
    x = np.diff(rng.standard_normal(n + 1))
    return x * env(n, 0.001, d) * 0.5


def clap():
    n = int(0.18 * SR)
    x = np.diff(rng.standard_normal(n + 1))
    tt = np.arange(n) / SR
    e = np.exp(-tt / 0.06) * (1 + 0.8 * np.sin(2 * np.pi * 70 * tt) ** 2)
    return x * e * 0.35


# F - G - Em - Am  (明るめの王道進行)
CHORDS = [
    (41, [65, 69, 72, 76]),   # Fmaj7
    (43, [67, 71, 74, 79]),   # G
    (40, [64, 67, 71, 74]),   # Em7
    (45, [69, 72, 76, 79]),   # Am
]
ARP = [0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 3, 1, 2]

bgm = np.zeros((N, 2), dtype=np.float32)
n_bars = int(total / BAR) + 1
outro_cut = scene_cuts["outro"]
for bar in range(n_bars):
    t0 = bar * BAR
    root, ch = CHORDS[bar % 4]
    drums = bar >= 2 and t0 < outro_cut + BAR
    # pad
    padlen = BAR * 1.02
    n = int(padlen * SR)
    tt = np.arange(n) / SR
    pe = np.minimum(tt / 0.25, 1) * np.minimum((padlen - tt) / 0.3, 1)
    for k, m in enumerate(ch[:3]):
        for det, pan in ((0.997, -0.5), (1.003, 0.5)):
            add(bgm, t0, tone(note(m - 12) * det, padlen, "tri") * pe, 0.05, pan)
    # bass (8分)
    for k in range(8):
        if not drums and k % 2:
            continue
        d = BEAT / 2
        sig = tone(note(root - 12 if k % 4 != 3 else root), d * 0.95, "saw")
        sig = sig * env(len(sig), 0.004, 0.16)
        add(bgm, t0 + k * d, sig, 0.26)
    # arp (16分)
    for k in range(16):
        d = BEAT / 4
        m = ch[ARP[k]] + (12 if (bar % 2 and k >= 8) else 0)
        sig = tone(note(m), 0.3, "tri")
        sig = sig * env(len(sig), 0.002, 0.09)
        g = 0.13 if k % 4 == 0 else 0.09
        add(bgm, t0 + k * d, sig, g, pan=0.45 * (-1) ** k)
        add(bgm, t0 + k * d + BEAT * 0.75, sig, g * 0.3, pan=-0.45 * (-1) ** k)  # delay
    if drums:
        for b in range(4):
            add(bgm, t0 + b * BEAT, kick(), 0.6)
            add(bgm, t0 + b * BEAT + BEAT / 2, hat(0.045), 0.16, 0.2)
            for s in (0.25, 0.75):
                add(bgm, t0 + (b + s) * BEAT, hat(0.02), 0.07, -0.2)
            if b in (1, 3):
                add(bgm, t0 + b * BEAT, clap(), 0.3)

# フェードイン/アウト
tt = np.arange(N) / SR
fade = np.minimum(tt / 0.3, 1) * np.clip((total - tt) / 1.4, 0, 1)
bgm *= fade[:, None]

# ダッキング: ナレーション中はBGMを下げる
win = int(0.05 * SR)
level = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, mode="same"))
duck_t = (level > 0.02).astype(np.float32)
k = int(0.25 * SR)
duck = np.convolve(duck_t, np.ones(k) / k, mode="same")
bgm *= (1.0 - 0.5 * duck)[:, None]
bgm *= 0.5

# ---------------------------------------------------------------- SFX
sfx = np.zeros((N, 2), dtype=np.float32)


def whoosh():
    n = int(0.34 * SR)
    tt = np.arange(n) / SR
    x = np.diff(rng.standard_normal(n + 1))
    e = np.sin(np.pi * tt / tt[-1]) ** 2
    return x * e * 0.25


def blip(f0=660, f1=1320):
    n = int(0.22 * SR)
    tt = np.arange(n) / SR
    f = f0 + (f1 - f0) * np.minimum(tt / 0.05, 1)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.07)


for sc, ct in scene_cuts.items():
    if sc == "intro":
        continue
    add(sfx, max(0, ct - 0.12), whoosh(), 0.5)
    add(sfx, ct + 0.1, blip(), 0.16)
    add(sfx, ct + 0.19, blip(990, 1980), 0.12)

mix = bgm + sfx + voice[:, None]
peak = np.abs(mix).max()
if peak > 0.97:
    mix *= 0.97 / peak

with wave.open(os.path.join(OUT, "audio.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

json.dump({"total": round(total, 3), "lines": timeline, "scene_cuts": scene_cuts},
          open(os.path.join(OUT, "timeline.json"), "w"), ensure_ascii=False, indent=1)
print(f"total {total:.2f}s  scenes {scene_cuts}")
