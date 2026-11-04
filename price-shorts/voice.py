"""VOICEVOX エンジン (localhost:50021) で各シーンのナレーションを合成し、timeline.json を作る。"""
import json, sys, wave, urllib.request, urllib.parse, pathlib

HERE = pathlib.Path(__file__).parent
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((HERE / "script.json").read_text())
API = "http://localhost:50021"

def post(path, params, body=None):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req).read()

t = 0.6  # 冒頭の無音
timeline = []
for sc in cfg["scenes"]:
    spk = cfg["speaker_hot"] if sc["style"] == "hot" else cfg["speaker_normal"]
    q = json.loads(post("/audio_query", {"text": sc["text"], "speaker": spk}))
    q["speedScale"] = cfg["speed"]
    q["prePhonemeLength"] = 0.05
    q["postPhonemeLength"] = 0.05
    q["outputSamplingRate"] = 48000
    wav = post("/synthesis", {"speaker": spk}, q)
    # アクセント句ごとの開始時刻（字幕・演出の同期用）
    phrases, pt = [], q["prePhonemeLength"]
    for ap in q["accent_phrases"]:
        kana = "".join(m["text"] for m in ap["moras"])
        phrases.append({"t": round(pt / q["speedScale"], 3), "kana": kana})
        for m in ap["moras"]:
            pt += (m.get("consonant_length") or 0) + m["vowel_length"]
        if ap.get("pause_mora"):
            pt += ap["pause_mora"]["vowel_length"]
    p = OUT / f"{sc['id']}.wav"
    p.write_bytes(wav)
    with wave.open(str(p)) as w:
        dur = w.getnframes() / w.getframerate()
    print(f"{sc['id']:8s} {dur:5.2f}s  {q['kana']}")
    timeline.append({**sc, "start": round(t, 3), "voiceDur": round(dur, 3),
                     "end": round(t + dur + sc["tail"], 3), "phrases": phrases})
    t += dur + sc["tail"]

(OUT / "timeline.json").write_text(json.dumps({"total": round(t, 3), "scenes": timeline}, ensure_ascii=False, indent=1))
print("total", round(t, 2))
