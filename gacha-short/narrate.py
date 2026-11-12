"""VOICEVOX(四国めたん)でナレーションを生成し、タイミング情報を書き出す。
事前に VOICEVOX エンジンを 127.0.0.1:50021 で起動しておくこと。"""
import json, urllib.request, urllib.parse, wave, io, struct, sys

ENGINE = "http://127.0.0.1:50021"
SPEAKER = 2          # 四国めたん(ノーマル)
SPEED = 1.12
GAP = 0.28           # 文と文の間の無音(秒)
LEAD = 0.35          # 冒頭の無音
TAIL = 1.3           # 末尾の余韻

# (シーンID, [(字幕チャンク, 読み上げテキスト), ...])  *強調* は字幕でハイライト。
# チャンク同士は読点(ポーズ)でつなぎ、ポーズ位置から字幕の切り替え時刻を求める。
LINES = [
    ("hook",    [("ガチャガチャって、\n*誰が考えてるか*知ってる?", "ガチャガチャって、誰が考えてるか、知ってる?")]),
    ("planner", [("実は*「企画担当者」*という\n専門の人がいるのよ。", "実は、企画担当者という、専門の人がいるのよ。")]),
    ("idea",    [("仕事はまず、*ネタ探し*。", "仕事はまず、ネタ探し"),
                 ("*SNSの流行*や、\n日常の*「あるある」*から", "SNSの流行や、日常のあるあるから"),
                 ("アイデアを出すの。", "アイデアを出すの。")]),
    ("limit",   [("でも、*条件は厳しい*わ。", "でも、条件は厳しいわ"),
                 ("*直径およそ5cm*の\nカプセルに入って、", "直径およそ5センチのカプセルに入って"),
                 ("*300円〜500円*で\n採算が取れること。", "300円から500円で、採算が取れること。")]),
    ("flow",    [("会議を通ったら、", "会議を通ったら"),
                 ("*試作*と、*工場*とのやり取り。", "試作と、工場とのやり取り"),
                 ("発売まで、*半年から1年*\nかかることも多いの。", "発売まで、半年から1年かかることも多いの。")]),
    ("solo",    [("しかも、*一人で*\n発案から発売まで担当して、", "しかも、一人で発案から発売まで担当して"),
                 ("*何本も同時進行*。", "何本も同時進行。")]),
    ("rush",    [("毎月、*数百種類*もの\n新作が出る、", "毎月、数百種類もの新作が出る"),
                 ("*超激戦区*なのよ。", "超激戦区なのよ。")]),
    ("end",     [("次にガチャを回すときは、", "次にガチャを回すときは"),
                 ("企画した人の*こだわり*も、\n想像してみてね。", "企画した人のこだわりも、想像してみてね。")]),
]

def post(path, params, body=None):
    url = f"{ENGINE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=body if body is not None else b"", method="POST",
                                 headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(req).read()

SR = 48000
pcm = bytearray(b"\x00\x00" * int(SR * LEAD))
timings = []
for sid, chunks in LINES:
    text = "、".join(c[1] for c in chunks)
    q = json.loads(post("/audio_query", {"text": text, "speaker": SPEAKER}))
    q.update(speedScale=SPEED, intonationScale=1.25, outputSamplingRate=SR, outputStereo=False,
             prePhonemeLength=0.05, postPhonemeLength=0.05, volumeScale=1.0)
    print(sid, q["kana"], file=sys.stderr)
    wav = post("/synthesis", {"speaker": SPEAKER}, json.dumps(q).encode())
    with wave.open(io.BytesIO(wav)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2
        frames = w.readframes(w.getnframes())
    start = len(pcm) / 2 / SR
    # ポーズ(読点)の時刻をモーラ長から算出
    t = q["prePhonemeLength"]; pauses = []
    for ap in q["accent_phrases"]:
        for m in ap["moras"]:
            t += (m.get("consonant_length") or 0) + m["vowel_length"]
        if ap.get("pause_mora"):
            pl = ap["pause_mora"]["vowel_length"] * q.get("pauseLengthScale", 1)
            pauses.append(t + pl / 2); t += pl
    pauses = [start + p / SPEED for p in pauses]
    # 各チャンクが消費するポーズ数 = チャンク内の読点数 + 1(最後のチャンクを除く)
    need = sum(c[1].count("、") + 1 for c in chunks) - 1
    assert len(pauses) == need, (sid, len(pauses), need)
    pcm += frames
    end = len(pcm) / 2 / SR
    pcm += b"\x00\x00" * int(SR * GAP)
    cs, k, cstart = [], 0, start
    for cap, spoken in chunks:
        k += spoken.count("、") + 1
        cend = pauses[k - 1] if k - 1 < len(pauses) else end
        cs.append({"caption": cap, "start": round(cstart, 3), "end": round(cend, 3)})
        cstart = cend
    timings.append({"id": sid, "start": round(start, 3), "end": round(end, 3), "chunks": cs})
pcm += b"\x00\x00" * int(SR * TAIL)
total = len(pcm) / 2 / SR
with wave.open("build/voice.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bytes(pcm))
json.dump({"total": round(total, 3), "lines": timings}, open("build/timings.json", "w"), ensure_ascii=False, indent=1)
print("total", total, file=sys.stderr)
