# Generates narration WAVs + caption timings with VOICEVOX (四国めたん ノーマル, speaker id 2).
# Requires a running engine:  docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
import json, os, re, sys, urllib.parse, urllib.request, wave

ENGINE = "http://localhost:50021"
SPEAKER = 2          # 四国めたん ノーマル
SPEED = 1.3

# (scene key, text to speak, caption text). Captions must keep the same punctuation as the spoken text.
LINES = [
    ("hook", "日本一うまいご当地ラーメン、どこだと思う？",
             "日本一うまいご当地ラーメン、どこだと思う？"),
    ("r10",  "第10位、和歌山ラーメン。豚骨醤油に、はやずしを合わせるのが和歌山流よ。",
             "第10位、和歌山ラーメン。豚骨醤油に、早寿司を合わせるのが和歌山流よ。"),
    ("r9",   "第9位、函館塩ラーメン。透き通った塩スープが、上品ね。",
             "第9位、函館塩ラーメン。透き通った塩スープが、上品ね。"),
    ("r8",   "第8位、旭川醤油ラーメン。ラードの膜で、最後まで熱々なの。",
             "第8位、旭川醤油ラーメン。ラードの膜で、最後まで熱々なの。"),
    ("r7",   "第7位、熊本ラーメン。焦がしにんにくのマー油が、香ばしいわ。",
             "第7位、熊本ラーメン。焦がしにんにくのマー油が、香ばしいわ。"),
    ("r6",   "第6位、徳島ラーメン。甘辛い豚バラに、生卵を絡めて召し上がれ。",
             "第6位、徳島ラーメン。甘辛い豚バラに、生卵を絡めて召し上がれ。"),
    ("r5",   "第5位、尾道ラーメン。魚介醤油に、せあぶらがぷかぷか浮いているの。",
             "第5位、尾道ラーメン。魚介醤油に、背脂がぷかぷか浮いているの。"),
    ("r4",   "第4位、横浜の家系ラーメン。豚骨醤油に太麺、ライスとの相性も最高よ。",
             "第4位、横浜の家系ラーメン。豚骨醤油に太麺、ライスとの相性も最高よ。"),
    ("r3",   "ここからトップスリー！第3位、喜多方ラーメン。朝から食べる、あさラー文化が有名よ。",
             "ここからTOP3！第3位、喜多方ラーメン。朝から食べる、朝ラー文化が有名よ。"),
    ("r2",   "第2位、札幌味噌ラーメン。濃厚な味噌に、炒め野菜たっぷりの一杯ね。",
             "第2位、札幌味噌ラーメン。濃厚な味噌に、炒め野菜たっぷりの一杯ね。"),
    ("r1a",  "そして、栄えある第1位は！",
             "そして、栄えある第1位は！"),
    ("r1b",  "博多ラーメン！濃厚豚骨に極細麺、替え玉まで楽しめる王者よ。",
             "博多ラーメン！濃厚豚骨に極細麺、替え玉まで楽しめる王者よ。"),
    ("outro","あなたの推しは何位だった？コメントで教えてね！",
             "あなたの推しは何位だった？コメントで教えてね！"),
]
PUNCT = r"[、。！？]"
MAX_CAPTION = 16     # merge short chunks up to this many characters per caption


def post(path, params, body=None):
    url = f"{ENGINE}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=120).read()


def chunks(text):
    return [c for c in re.findall(rf"[^、。！？]+{PUNCT}*", text) if c.strip()]


def caption_times(q, speak, caption, total):
    """Caption segments timed at the pauses VOICEVOX inserts for punctuation."""
    sp, cp = chunks(speak), chunks(caption)
    t = q["prePhonemeLength"]
    bounds = []
    for ap in q["accent_phrases"]:
        t += sum((m.get("consonant_length") or 0) + m["vowel_length"] for m in ap["moras"])
        if ap.get("pause_mora"):
            bounds.append(t / SPEED)
            t += ap["pause_mora"]["vowel_length"]
    t0 = q["prePhonemeLength"] / SPEED
    if len(cp) != len(sp) or len(bounds) < len(sp) - 1:
        # fall back to splitting time by character count
        n = sum(len(c) for c in cp); acc = 0; bounds = []
        for c in cp[:-1]:
            acc += len(c); bounds.append(t0 + (total - t0) * acc / n)
    ends = bounds[:len(cp) - 1] + [total]
    segs, start = [], 0.0
    for c, e in zip(cp, ends):
        if segs and len(segs[-1]["text"]) + len(c) <= MAX_CAPTION and not re.search(r"[。！？]$", segs[-1]["text"]):
            segs[-1]["text"] += c; segs[-1]["t1"] = round(e, 3)
        else:
            segs.append(dict(t0=round(start, 3), t1=round(e, 3), text=c))
        start = e
    for s in segs:
        s["text"] = re.sub(r"、$", "", s["text"])
    return segs


out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
os.makedirs(out_dir, exist_ok=True)
for f in os.listdir(out_dir):
    if f.endswith(".wav"):
        os.remove(os.path.join(out_dir, f))
durations, captions = {}, {}
for key, speak, caption in LINES:
    q = json.loads(post("/audio_query", {"text": speak, "speaker": SPEAKER}))
    q["speedScale"] = SPEED
    q["intonationScale"] = 1.15
    q["prePhonemeLength"] = 0.05
    q["postPhonemeLength"] = 0.08
    wav = post("/synthesis", {"speaker": SPEAKER}, q)
    path = os.path.join(out_dir, f"{key}.wav")
    open(path, "wb").write(wav)
    with wave.open(path) as w:
        durations[key] = round(w.getnframes() / w.getframerate(), 3)
    captions[key] = caption_times(q, speak, caption, durations[key])
    print(key, durations[key], [c["text"] for c in captions[key]])
json.dump(durations, open(os.path.join(out_dir, "durations.json"), "w"), indent=1)
json.dump(captions, open(os.path.join(out_dir, "captions.json"), "w"), ensure_ascii=False, indent=1)
