"""VOICEVOX(四国めたん)でナレーションを合成し、タイムラインを書き出す。

事前に VOICEVOX エンジンを起動しておく:
  docker run -d -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-latest
"""
import json
import pathlib
import urllib.parse
import urllib.request
import wave

import numpy as np

ENGINE = "http://127.0.0.1:50021"
SPEAKER = 2  # 四国めたん(ノーマル)
SR = 48000
OUT = pathlib.Path(__file__).parent / "output"

# (シーン, 字幕, 読み上げテキスト(省略時は字幕と同じ), 直後の無音秒)
LINES = [
    ("hook", "探偵の仕事って、\n実は「推理」じゃないのよ。", "探偵の仕事って、実は、推理じゃないのよ。", 0.35),
    ("truth", "本当の仕事は、依頼人に代わって\n事実を調べること。", None, 0.15),
    ("truth", "そして、証拠を集めて\n報告することなの。", None, 0.35),
    ("requests", "依頼でいちばん多いのは、\n浮気調査。", "依頼でいちばん多いのは、浮気調査。", 0.15),
    ("requests", "ほかにも、人探しや\n企業の信用調査があるわ。", "ほかにも、人探しや、企業の信用調査があるわ。", 0.35),
    ("methods", "調査の基本は、この三つ。", "調査の基本は、この三つ。", 0.1),
    ("methods", "尾行、張り込み、聞き込み。", "尾行。張り込み。聞き込み。", 0.15),
    ("methods", "何時間も、じっと\n待ち続けることもあるの。", None, 0.35),
    ("limits", "でも、探偵に\n特別な権限はないわ。", None, 0.15),
    ("limits", "住居侵入や盗聴は、\nもちろん違法よ。", "住居侵入や、盗聴は、もちろん違法よ。", 0.35),
    ("license", "日本では資格はいらないけれど、", "にほんでは資格はいらないけれど、", 0.05),
    ("license", "公安委員会への\n届け出が必要なの。", "公安委員会への、届け出が必要なの。", 0.35),
    ("outro", "地道で、忍耐のいる仕事。", None, 0.15),
    ("outro", "それが、本当の探偵よ。", None, 1.6),
]

LEAD_IN = 0.4


def post(path, params, body=None):
    url = f"{ENGINE}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(req).read()


def synth(text):
    q = json.loads(post("/audio_query", {"text": text, "speaker": SPEAKER}))
    q.update(speedScale=1.08, intonationScale=1.25, prePhonemeLength=0.05,
             postPhonemeLength=0.05, outputSamplingRate=SR, outputStereo=False,
             volumeScale=1.0)
    raw = post("/synthesis", {"speaker": SPEAKER}, q)
    tmp = OUT / "_tmp.wav"
    tmp.write_bytes(raw)
    with wave.open(str(tmp)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    tmp.unlink()
    # アクセント句ごとの開始時刻(演出のキュー合わせ用)
    t = q["prePhonemeLength"]
    phrases = []
    for ap in q["accent_phrases"]:
        start = t
        for m in ap["moras"]:
            t += (m.get("consonant_length") or 0) + m["vowel_length"]
        phrases.append({"kana": "".join(m["text"] for m in ap["moras"]),
                        "start": start / q["speedScale"]})
        if ap.get("pause_mora"):
            t += ap["pause_mora"]["vowel_length"]
    return pcm.astype(np.float32) / 32768, phrases


def main():
    OUT.mkdir(exist_ok=True)
    chunks, timeline, t = [np.zeros(int(LEAD_IN * SR), np.float32)], [], LEAD_IN
    for scene, caption, reading, gap in LINES:
        pcm, phrases = synth(reading or caption.replace("\n", ""))
        dur = len(pcm) / SR
        timeline.append({
            "scene": scene, "caption": caption, "start": round(t, 3),
            "end": round(t + dur, 3),
            "phrases": [{"kana": p["kana"], "t": round(t + p["start"], 3)} for p in phrases],
        })
        chunks += [pcm, np.zeros(int(gap * SR), np.float32)]
        t += dur + gap
    audio = np.concatenate(chunks)
    audio *= 0.89 / np.abs(audio).max()
    with wave.open(str(OUT / "narration.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())
    total = round(len(audio) / SR, 3)
    (OUT / "timeline.json").write_text(
        json.dumps({"duration": total, "lines": timeline}, ensure_ascii=False, indent=1))
    for l in timeline:
        print(f'{l["start"]:6.2f}-{l["end"]:6.2f} [{l["scene"]}]',
              " ".join(f'{p["kana"]}@{p["t"]:.2f}' for p in l["phrases"]))
    print("total", total)


if __name__ == "__main__":
    main()
