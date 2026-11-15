"""VOICEVOXエンジン(localhost:50021)で四国めたんのナレーションを合成する"""
import json, os, sys, urllib.parse, urllib.request, wave

sys.path.insert(0, os.path.dirname(__file__))
from script import INTRO, ITEMS, OUTRO

HOST = "http://localhost:50021"
SPEAKER = 2  # 四国めたん ノーマル
OUT = os.path.join(os.path.dirname(__file__), "build", "voice")
os.makedirs(OUT, exist_ok=True)


READING = {"芦生": "あしう", "10選": "じっせん"}  # 読み補正


def synth(text, path, speed=1.2):
    for k, v in READING.items():
        text = text.replace(k, v)
    q = urllib.parse.urlencode({"text": text, "speaker": SPEAKER})
    with urllib.request.urlopen(urllib.request.Request(f"{HOST}/audio_query?{q}", method="POST")) as r:
        query = json.load(r)
    query.update(speedScale=speed, intonationScale=1.15, pitchScale=0.02,
                 prePhonemeLength=0.05, postPhonemeLength=0.08, outputSamplingRate=48000)
    req = urllib.request.Request(f"{HOST}/synthesis?speaker={SPEAKER}", data=json.dumps(query).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r, open(path, "wb") as f:
        f.write(r.read())
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


segments = []  # 各シーン: {"kind", "rank", "lines": [{"text","wav","dur"}]}
scenes = [("intro", None, INTRO)] + [("item", it[0], it[4]) for it in ITEMS] + [("outro", None, OUTRO)]
for si, (kind, rank, lines) in enumerate(scenes):
    out = []
    for li, text in enumerate(lines):
        p = os.path.join(OUT, f"s{si:02d}_{li}.wav")
        out.append({"text": text, "wav": p, "dur": synth(text, p)})
        print(f"{p}: {out[-1]['dur']:.2f}s  {text}")
    segments.append({"kind": kind, "rank": rank, "lines": out})

json.dump(segments, open(os.path.join(OUT, "..", "voice.json"), "w"), ensure_ascii=False, indent=1)
