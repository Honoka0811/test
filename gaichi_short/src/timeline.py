import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
VOICE = os.path.join(HERE, "voice")

# scene key -> (lead before voice, tail after voice)
PAD = {
    "hook": (0.35, 0.35), "title": (0.15, 0.55),
    "tease": (0.2, 1.1), "r1": (0.15, 1.3),
    "extra": (0.25, 0.3), "outro": (0.2, 2.6),
}
DEFAULT_PAD = (0.15, 0.45)

def build():
    meta = json.load(open(os.path.join(VOICE, "meta.json")))
    t = 0.0
    scenes = []
    for m in meta:
        lead, tail = PAD.get(m["key"], DEFAULT_PAD)
        s = {"key": m["key"], "start": round(t, 3), "vstart": round(t + lead, 3), "vdur": m["dur"]}
        t += lead + m["dur"] + tail
        s["end"] = round(t, 3)
        scenes.append(s)
    return scenes, t

if __name__ == "__main__":
    sc, total = build()
    for s in sc:
        print(s)
    print("total", total)
