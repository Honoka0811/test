# Generates narration WAVs with VOICEVOX (四国めたん ノーマル, speaker id 2).
# Requires a running engine:  docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
import json, urllib.parse, urllib.request, wave, os, sys

ENGINE = "http://localhost:50021"
SPEAKER = 2          # 四国めたん ノーマル
SPEED = 1.15

# (scene key, text to speak). Readings written in kana where the engine may misread.
LINES = [
    ("intro",    "全国のご当地ラーメン、トップテンを発表するわ！"),
    ("r10",      "第10位、和歌山ラーメン。豚骨醤油のスープに、はやずしを合わせるのが和歌山流よ。"),
    ("r9",       "第9位、函館塩ラーメン。透き通った塩スープが、あっさり上品な味わいね。"),
    ("r8",       "第8位、旭川醤油ラーメン。魚介と豚骨のダブルスープを、ラードで熱々に閉じ込めているの。"),
    ("r7",       "第7位、熊本ラーメン。豚骨スープに、香ばしいマー油がたまらないわ。"),
    ("r6",       "第6位、徳島ラーメン。甘辛い豚バラ肉に、生卵を絡めて召し上がれ。"),
    ("r5",       "第5位、尾道ラーメン。魚介醤油のスープに、せあぶらのミンチが浮かんでいるのが特徴よ。"),
    ("r4",       "第4位、横浜の家系ラーメン。豚骨醤油にチーユ、太麺とのからみが最高ね。"),
    ("r3",       "第3位、喜多方ラーメン。あっさり醤油に平打ち縮れ麺。朝から食べる、あさラー文化も有名よ。"),
    ("r2",       "第2位、札幌味噌ラーメン。濃厚な味噌スープに、炒め野菜たっぷりの一杯ね。"),
    ("r1",       "そして第1位は、博多ラーメン！濃厚豚骨に極細麺、替え玉まで楽しめる王者よ。"),
    ("outro",    "ちなみに、日本三大ラーメンは、札幌、博多、喜多方。あなたの推しは何位だったかしら？コメントで教えてね。"),
]

def post(path, params, body=None):
    url = f"{ENGINE}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=120).read()

out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(out_dir, exist_ok=True)
durations = {}
for key, text in LINES:
    q = json.loads(post("/audio_query", {"text": text, "speaker": SPEAKER}))
    q["speedScale"] = SPEED
    q["prePhonemeLength"] = 0.05
    q["postPhonemeLength"] = 0.1
    wav = post("/synthesis", {"speaker": SPEAKER}, q)
    path = os.path.join(out_dir, f"{key}.wav")
    open(path, "wb").write(wav)
    with wave.open(path) as w:
        durations[key] = round(w.getnframes() / w.getframerate(), 3)
    print(key, durations[key])
json.dump(durations, open(os.path.join(out_dir, "durations.json"), "w"), indent=1)
