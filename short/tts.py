# VOICEVOX エンジン(localhost:50021)でナレーションを生成し、タイミング情報を書き出す
import json, wave, urllib.request, urllib.parse, os
from script import SCENES

API = "http://localhost:50021"
os.makedirs("build/voice", exist_ok=True)


def post(path, params, body=None):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req).read()


timeline = []
t = 0.6  # 冒頭の間
GAP_LINE, GAP_SCENE = 0.12, 0.45
for si, sc in enumerate(SCENES):
    scene = dict(kind=sc["kind"], num=sc.get("num"), title=sc.get("title"),
                 sub=sc.get("sub"), start=t, lines=[])
    if sc["kind"] == "habit":
        t += 0.35  # 番号の登場演出ぶんの間
    for li, (cap, speech, style) in enumerate(sc["lines"]):
        q = json.loads(post("/audio_query", {"text": speech, "speaker": style}))
        q["speedScale"] = 1.18
        q["intonationScale"] = 1.25 if style == 81 else 1.1
        q["prePhonemeLength"] = 0.05
        q["postPhonemeLength"] = 0.05
        q["outputSamplingRate"] = 48000
        wav = post("/synthesis", {"speaker": style}, q)
        path = f"build/voice/{si:02d}_{li:02d}.wav"
        open(path, "wb").write(wav)
        with wave.open(path) as w:
            dur = w.getnframes() / w.getframerate()
        scene["lines"].append(dict(cap=cap, wav=path, start=t, dur=dur))
        t += dur + GAP_LINE
    t += GAP_SCENE
    scene["end"] = t
    timeline.append(scene)

total = t + 0.8
json.dump(dict(total=total, scenes=timeline), open("build/timeline.json", "w"),
          ensure_ascii=False, indent=1)
print(f"total {total:.2f}s")
