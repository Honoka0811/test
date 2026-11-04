"""Synthesize narration with VOICEVOX (四国めたん) and build timing.json.
usage: python3 synth.py [--placeholder]
"""
import json, sys, os, wave, urllib.request, urllib.parse
import numpy as np
from scenes import SCENES

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "narr"); os.makedirs(OUT, exist_ok=True)
API = "http://127.0.0.1:50021"
GAP = 0.12


def speaker_id():
    sp = json.load(urllib.request.urlopen(API + "/speakers"))
    for s in sp:
        if s["name"] == "四国めたん":
            for st in s["styles"]:
                if st["name"] == "ノーマル":
                    return st["id"]
    raise SystemExit("四国めたん not found")


def tts(text, sid, path):
    q = urllib.request.urlopen(urllib.request.Request(
        f"{API}/audio_query?" + urllib.parse.urlencode({"text": text, "speaker": sid}), method="POST")).read()
    q = json.loads(q)
    from kana import KANA
    if text not in KANA: raise SystemExit("no kana for: " + text)
    ap = urllib.request.urlopen(urllib.request.Request(
        f"{API}/accent_phrases?" + urllib.parse.urlencode({"text": KANA[text], "speaker": sid, "is_kana": "true"}), method="POST")).read()
    q["accent_phrases"] = json.loads(ap)
    q.update(speedScale=1.18, intonationScale=1.25, pitchScale=0.02, volumeScale=1.3,
             prePhonemeLength=0.03, postPhonemeLength=0.05, outputSamplingRate=44100)
    wav = urllib.request.urlopen(urllib.request.Request(
        f"{API}/synthesis?speaker={sid}", data=json.dumps(q).encode(),
        headers={"Content-Type": "application/json"}, method="POST")).read()
    open(path, "wb").write(wav)


def wav_dur(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def main():
    placeholder = "--placeholder" in sys.argv
    sid = None if placeholder else speaker_id()
    t = 0.0
    timing = []
    for sc in SCENES:
        start = t
        cur = sc["lead"]
        sents = []
        for i, (sub, say) in enumerate(sc["sents"]):
            p = os.path.join(OUT, f"{sc['id']}_{i}.wav")
            if placeholder:
                d = len(say) / 9.0
                with wave.open(p, "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
                    w.writeframes(np.zeros(int(d * 44100), np.int16).tobytes())
            else:
                tts(say, sid, p)
            d = wav_dur(p)
            sents.append(dict(sub=sub, file=p, start=cur, dur=d))
            cur += d + GAP
        dur = cur - GAP + sc["tail"]
        timing.append(dict(id=sc["id"], start=start, dur=dur, sents=sents))
        t += dur
    json.dump(dict(total=t, scenes=timing), open(os.path.join(D, "timing.json"), "w"), ensure_ascii=False, indent=1)
    print("total", round(t, 2), "sec")


main()
