# -*- coding: utf-8 -*-
"""VOICEVOX エンジン（http://127.0.0.1:50021）で 青山龍星 のナレーションを生成する。
文（「。」区切り）ごとに合成して結合し、字幕用のタイミングを timings.json に書き出す。
使い方: python3 make_voice.py <out_dir>
"""
import sys, os, json, re, wave, urllib.request, urllib.parse
from scenario import SCENES

BASE = "http://127.0.0.1:50021"
SPEAKER = 13  # 青山龍星 ノーマル
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
GAP = 0.25  # 文と文の間の無音（秒）

# 誤読対策：ユーザー辞書に登録する語（表記, 読み, アクセント核）
USER_DICT = [
    ("安定性", "アンテイセイ", 0),          # 「やすていせい」と誤読されるため
    ("リンクルリペア", "リンクルリペア", 5), # 単語が分割されるため
    ("朝用", "アサヨウ", 0),               # 「ちょうよう」と誤読されるため
]
# 合成時だけ置き換える表記（字幕は元の表記のまま）
SYNTH_REPLACE = {
    "D-UVシールド": "ディーユーブイシールド",
}

def post(path, params, body=None):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read())

def register_user_dict():
    existing = {w["surface"] for w in get("/user_dict").values()}
    for surface, pron, acc in USER_DICT:
        if surface in existing: continue
        post("/user_dict_word", {"surface": surface, "pronunciation": pron, "accent_type": acc,
                                 "word_type": "PROPER_NOUN", "priority": 9})
        print("user_dict +", surface, pron)

def synth(text):
    for k, v in SYNTH_REPLACE.items():
        text = text.replace(k, v)
    q = json.loads(post("/audio_query", {"text": text, "speaker": SPEAKER}))
    q["speedScale"] = 1.12          # テンポよく
    q["intonationScale"] = 1.15     # 抑揚を少し強め
    q["prePhonemeLength"] = 0.05
    q["postPhonemeLength"] = 0.08
    q["outputSamplingRate"] = 48000
    q["outputStereo"] = False
    return post("/synthesis", {"speaker": SPEAKER}, q)

def read_wav(b):
    import io
    with wave.open(io.BytesIO(b)) as w:
        assert w.getframerate() == 48000 and w.getnchannels() == 1 and w.getsampwidth() == 2
        return w.readframes(w.getnframes())

register_user_dict()
timings = []
for i, sc in enumerate(SCENES):
    sentences = [s + "。" for s in re.split(r"。", sc["narration"]) if s.strip()]
    frames = b""; cues = []; t = 0.0
    for s in sentences:
        pcm = read_wav(synth(s))
        dur = len(pcm) / 2 / 48000
        cues.append(dict(text=s, start=round(t, 3), end=round(t + dur, 3)))
        frames += pcm + b"\x00" * int(GAP * 48000) * 2
        t += dur + GAP
    frames = frames[: len(frames) - int(GAP * 48000) * 2]  # 末尾のギャップは除く
    path = os.path.join(OUT, f"{i:02d}_{sc['id']}.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000); w.writeframes(frames)
    total = len(frames) / 2 / 48000
    timings.append(dict(scene=sc["id"], file=path, duration=round(total, 3), cues=cues))
    print("voice", i, sc["id"], f"{total:.1f}s", len(sentences), "sentences")

json.dump(timings, open(os.path.join(OUT, "timings.json"), "w"), ensure_ascii=False, indent=1)
