"""VOICEVOX ENGINE（http://127.0.0.1:50021）で四国めたんのナレーションを生成する。

VOICEVOX アプリを起動しておけばエンジンも立ち上がる。
  python tts.py            # out/voice/00.wav ... を生成
"""
import json, os, sys, urllib.parse, urllib.request

from scenes import SCENES

HOST = os.environ.get("VOICEVOX_HOST", "http://127.0.0.1:50021")
STYLE_NAMES = {"normal": "ノーマル", "whisper": "ささやき", "hiso": "ヒソヒソ"}
FALLBACK_IDS = {"normal": 2, "whisper": 36, "hiso": 37}  # 四国めたん
# スタイル別の調整（ささやき系は音量が小さいので持ち上げる）
TUNE = {
    "normal": dict(speedScale=1.17, pitchScale=-0.02, intonationScale=1.15, volumeScale=1.0),
    "whisper": dict(speedScale=1.05, pitchScale=0.0, intonationScale=1.0, volumeScale=1.9),
    "hiso": dict(speedScale=1.08, pitchScale=0.0, intonationScale=1.0, volumeScale=1.9),
}


def _req(path, data=None, method="GET"):
    req = urllib.request.Request(HOST + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def style_ids():
    ids = dict(FALLBACK_IDS)
    for sp in json.loads(_req("/speakers")):
        if sp["name"] == "四国めたん":
            names = {st["name"]: st["id"] for st in sp["styles"]}
            for k, n in STYLE_NAMES.items():
                if n in names:
                    ids[k] = names[n]
    return ids


def main(outdir="out/voice"):
    os.makedirs(outdir, exist_ok=True)
    ids = style_ids()
    print("四国めたん style ids:", ids)
    for i, s in enumerate(SCENES):
        sid = ids[s["style"]]
        q = json.loads(_req(f"/audio_query?text={urllib.parse.quote(s['text'])}&speaker={sid}",
                            method="POST"))
        q.update(TUNE[s["style"]])
        q.update(prePhonemeLength=0.05, postPhonemeLength=0.12, outputSamplingRate=48000)
        wav = _req(f"/synthesis?speaker={sid}", data=json.dumps(q).encode(), method="POST")
        path = os.path.join(outdir, f"{i:02d}.wav")
        with open(path, "wb") as f:
            f.write(wav)
        print("wrote", path, s["text"])


if __name__ == "__main__":
    main(*sys.argv[1:])
