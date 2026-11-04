import json, wave, numpy as np
from scenes import SCENES
SR = 44100
def load(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2: x = x.reshape(-1, 2)
        else: x = np.stack([x, x], 1)
        assert w.getframerate() == SR, (p, w.getframerate())
    return x
T = json.load(open("timing.json")); total = T["total"]
N = int(total * SR) + SR
voice = np.zeros((N, 2), np.float32); sfx = np.zeros((N, 2), np.float32)
def put(buf, x, t, g=1.0):
    s = int(t * SR); e = min(N, s + len(x)); buf[s:e] += x[: e - s] * g
S = {k: load(f"audio/{k}.wav") for k in ["whoosh", "impact", "coin", "pop", "drumroll", "shock", "fanfare"]}
cfg = {s["id"]: s for s in SCENES}
for sc in T["scenes"]:
    t0 = sc["start"]; c = cfg[sc["id"]]; k = c["kind"]
    for s in sc["sents"]:
        put(voice, load(s["file"]), t0 + s["start"])
    st = [s["start"] for s in sc["sents"]]
    if k == "hook":
        put(sfx, S["impact"], t0, 0.8); put(sfx, S["pop"], t0 + 0.35, 0.8); put(sfx, S["shock"], t0 + st[1], 0.6)
    elif k == "title":
        put(sfx, S["whoosh"], t0, 0.7); put(sfx, S["impact"], t0 + 0.2, 0.7)
    elif k == "rank":
        put(sfx, S["whoosh"], t0, 0.6); put(sfx, S["impact"], t0 + 0.12, 0.75)
        put(sfx, S["pop"], t0 + 0.3, 0.7); put(sfx, S["coin"], t0 + 1.5, 0.8)
        if c.get("surprise"): put(sfx, S["shock"], t0 + 0.55, 0.7)
        if c.get("champion"): put(sfx, S["fanfare"], t0 + 0.05, 0.9)
    elif k == "drumroll":
        put(sfx, S["whoosh"], t0, 0.6)
        put(sfx, S["drumroll"], t0 + sc["dur"] - 1.6, 1.0)
    elif k == "warn":
        put(sfx, S["impact"], t0, 0.9); put(sfx, S["shock"], t0 + st[2], 0.5)
    elif k == "cta":
        put(sfx, S["whoosh"], t0, 0.6)
        for i in range(6): put(sfx, S["pop"], t0 + 0.08 * i, 0.4)
        put(sfx, S["pop"], t0 + st[1], 0.8); put(sfx, S["coin"], t0 + sc["dur"] - 1.2, 0.7)
voice *= 0.92 / max(1e-6, np.abs(voice).max())
bgm = load("audio/bgm.wav")[:N]; bgm = np.pad(bgm, ((0, N - len(bgm)), (0, 0)))
# ducking envelope
v = np.abs(voice[:, 0]); hop = 441
env = np.array([v[i:i + hop].max() for i in range(0, N, hop)]) > 0.02
from scipy.ndimage import maximum_filter1d, uniform_filter1d
env = uniform_filter1d(maximum_filter1d(env.astype(float), 25), 15)
env = np.repeat(env, hop)[:N]
g = 0.55 - 0.33 * env
mix = voice + sfx * 0.7 + bgm * g[:, None]
# fade out end
fo = int(1.2 * SR); mix[int(total * SR) - fo:int(total * SR)] *= np.linspace(1, 0, fo)[:, None]
mix = mix[: int(total * SR)]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix *= 0.95 / np.abs(mix).max()
with wave.open("mix.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("mix ok", total)
