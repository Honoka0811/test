"""Generate narration with VOICEVOX (青山龍星) and build the beat-snapped timeline.

Each scene starts on a half-bar of the BGM grid so rank slams land on the beat.
Outputs build/voice/*.wav and build/timeline.json (consumed by render + audio).
"""
import json, os, wave, io, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build")
VOICE = os.path.join(OUT, "voice")
os.makedirs(VOICE, exist_ok=True)

API = "http://127.0.0.1:50021"
NORMAL, HOT = 13, 81  # 青山龍星: ノーマル / 熱血
BPM = 124
BEAT = 60 / BPM
HALF_BAR = BEAT * 2

# (display subtitle, tts reading, style, speed, extra gap after)
# words wrapped in 【】 are highlighted in the subtitle
SCENES = [
    dict(id="hook", lead=0.15, lines=[
        ("鍛えるだけで【得する筋肉】がある！", "きたえるだけで、とくする筋肉がある！", HOT, 1.15, 0.15),
        ("トップ5を一気に紹介！", "トップファイブを、いっきに紹介！", HOT, 1.15, 0.2),
    ]),
    dict(id="r5", rank=5, lead=0.45, lines=[
        ("第5位【大胸筋】！", "第五位、だいきょうきん！", HOT, 1.1, 0.2),
        ("胸に広がる、上半身の大きな筋肉", "胸に広がる、上半身の大きな筋肉。", NORMAL, 1.15, 0.1),
        ("【押す力】がアップ！上半身にメリハリ", "押す力がアップして、上半身にメリハリが出る！", NORMAL, 1.15, 0.1),
        ("おすすめは【腕立て伏せ】！", "おすすめは、うでたてふせ！", NORMAL, 1.15, 0.2),
    ]),
    dict(id="r4", rank=4, lead=0.45, lines=[
        ("第4位【広背筋】！", "第四位、こうはいきん！", HOT, 1.1, 0.2),
        ("脇から腰まで広がる、背中の筋肉", "わきから腰まで広がる、背中の筋肉。", NORMAL, 1.15, 0.1),
        ("【猫背が改善】！逆三角形の体に", "猫背が改善して、逆三角形の体に！", NORMAL, 1.15, 0.1),
        ("おすすめは【懸垂】！", "おすすめは、けんすい！", NORMAL, 1.15, 0.2),
    ]),
    dict(id="r3", rank=3, lead=0.45, lines=[
        ("第3位【体幹】！", "第三位、たいかん！", HOT, 1.1, 0.2),
        ("お腹まわりと背骨を支える筋肉の総称", "おなかまわりと、背骨を支える筋肉の総称だ。", NORMAL, 1.15, 0.1),
        ("姿勢が安定して【腰痛予防】に！", "姿勢が安定して、腰痛予防に！", NORMAL, 1.15, 0.1),
        ("おすすめは【プランク】！", "おすすめは、プランク！", NORMAL, 1.15, 0.2),
    ]),
    dict(id="r2", rank=2, lead=0.45, lines=[
        ("第2位【大臀筋】！", "第二位、だいでんきん！", HOT, 1.1, 0.2),
        ("お尻を覆う、単体で最大級の筋肉", "おしりを覆う、単体で最大級の筋肉。", NORMAL, 1.15, 0.1),
        ("【姿勢】も【走る力】もアップ！", "姿勢も、走る力もアップ！", NORMAL, 1.15, 0.1),
        ("おすすめは【ヒップリフト】！", "おすすめは、ヒップリフト！", NORMAL, 1.15, 0.2),
    ]),
    dict(id="build", lead=0.1, lines=[
        ("そして…栄えある第1位は…", "そして、はえある、第一位は", HOT, 1.0, 1.6),
    ]),
    dict(id="r1", rank=1, lead=0.45, lines=[
        ("【大腿四頭筋】！", "だいたいしとうきん！", HOT, 1.05, 0.2),
        ("太ももの前、体で一番大きな筋肉群", "太ももの前、体で一番大きな筋肉群だ。", NORMAL, 1.15, 0.1),
        ("【基礎代謝アップ】で太りにくい体に！", "基礎代謝が上がって、太りにくい体に！", NORMAL, 1.15, 0.1),
        ("おすすめは筋トレの王様【スクワット】！", "おすすめは、筋トレの王様、スクワット！", HOT, 1.12, 0.3),
    ]),
    dict(id="outro", lead=0.2, lines=[
        ("まずは【この3つ】から始めよう！", "まずは、この三つから始めよう！", NORMAL, 1.15, 0.15),
        ("【保存】して今日から実践だ！", "保存して、今日から実践だ！", HOT, 1.12, 1.6),
    ]),
]


def post(path, params, body=None):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return r.read()


def synth(text, style, speed, path):
    q = json.loads(post("/audio_query", {"text": text, "speaker": style}))
    q["speedScale"] = speed
    q["intonationScale"] = 1.25 if style == HOT else 1.1
    q["volumeScale"] = 1.2
    q["prePhonemeLength"] = 0.05
    q["postPhonemeLength"] = 0.08
    q["outputSamplingRate"] = 44100
    wav = post("/synthesis", {"speaker": style}, json.dumps(q).encode())
    with open(path, "wb") as f:
        f.write(wav)
    with wave.open(io.BytesIO(wav)) as w:
        return w.getnframes() / w.getframerate()


def snap(t):
    """Round up to the next half-bar."""
    n = -(-t // HALF_BAR)
    return n * HALF_BAR


def main():
    t = 0.0
    scenes = []
    for si, sc in enumerate(SCENES):
        start = snap(t) if si else 0.0
        cur = start + sc["lead"]
        lines = []
        for li, (disp, read, style, speed, gap) in enumerate(sc["lines"]):
            p = os.path.join(VOICE, f"{sc['id']}_{li}.wav")
            d = synth(read, style, speed, p)
            lines.append(dict(text=disp, start=round(cur, 3), dur=round(d, 3), wav=p))
            cur += d + gap
            print(f"{sc['id']:6s} {li} {cur:6.2f}s  {disp}")
        scenes.append(dict(id=sc["id"], rank=sc.get("rank"), start=round(start, 3),
                           lines=lines))
        t = cur
    end = snap(t)
    for a, b in zip(scenes, scenes[1:]):
        a["end"] = b["start"]
    scenes[-1]["end"] = end
    json.dump(dict(bpm=BPM, duration=end, scenes=scenes),
              open(os.path.join(OUT, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print("total", round(end, 2))


if __name__ == "__main__":
    main()
