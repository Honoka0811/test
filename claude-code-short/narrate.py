"""VOICEVOX（四国めたん）でナレーションを生成し、シーン尺を合わせて video.html を更新する。
使い方: python3 narrate.py <作業ディレクトリ>
前提: VOICEVOXエンジンが localhost:50021 で起動していること
  docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
"""
import json, re, sys, wave, urllib.request, urllib.parse, os

HOST = "http://localhost:50021"
SPEAKER = 2  # 四国めたん ノーマル
SPEED = 1.3
LEAD = 0.15   # シーン開始からナレーション開始まで
TAIL = 0.3   # ナレーション終了後の余白

# (ナレーション, 字幕, 最低シーン秒数)
SCENES = [
    ("クロードコードって知ってる？話題のAIエンジニアを、サクッと解説しますわ！",
     "Claude Codeって知ってる？", 2.5),
    ("ひとことで言えば、自分で手を動かすAI。アンソロピック製の、コーディングエージェントですの。",
     "ひとことで言えば<br>自分で手を動かすAI", 3.5),
    ("コードを読む、書く、実行する。ギットの操作まで、まるごとお任せ！",
     "読む・書く・実行する<br>Git操作までお任せ！", 3.5),
    ("使い方は、日本語で頼むだけ。調査も修正もテストも、自分で進めてくれますわ。",
     "日本語で頼むだけ<br>調査→修正→テストまで自動", 6.0),
    ("ターミナル、エディタ、アプリにウェブ。どこでも使えますの。",
     "ターミナル・エディタ・アプリ・Web<br>どこでも使える", 3.0),
    ("ルールの記憶に、外部ツール連携、自動化まで。カスタマイズも自在ですわ。",
     "ルール記憶・外部連携・自動化<br>カスタマイズも自在", 3.0),
    ("大事な操作は、ちゃんと許可を求めるから安心！",
     "大事な操作は<br>ちゃんと許可を求めるから安心", 3.0),
    ("まずは小さなタスクから、試してみてちょうだい！",
     "まずは小さなタスクから<br>試してみてね！", 3.5),
]

def post(path, params, body=None):
    url = f"{HOST}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req).read()

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    t, starts, ends, offsets = 0.0, [], [], []
    for i, (text, _, mindur) in enumerate(SCENES):
        q = json.loads(post("/audio_query", {"text": text, "speaker": SPEAKER}))
        q["speedScale"] = SPEED
        q["prePhonemeLength"] = 0.02
        q["intonationScale"] = 1.25
        q["pitchScale"] = 0.02
        for ph in q["accent_phrases"]:
            if ph.get("pause_mora"): ph["pause_mora"]["vowel_length"] *= 0.5
        q["postPhonemeLength"] = 0.05
        wav = post("/synthesis", {"speaker": SPEAKER}, q)
        path = os.path.join(out, f"n{i}.wav")
        open(path, "wb").write(wav)
        with wave.open(path) as w:
            d = w.getnframes() / w.getframerate()
        dur = max(mindur, LEAD + d + TAIL)
        starts.append(round(t, 2)); offsets.append(round(t + LEAD, 2))
        t += dur; ends.append(round(t, 2))
        print(f"scene{i+1}: {d:.2f}s voice -> {dur:.2f}s scene")
    total = round(t + 0.6, 2)  # 最後に少し余韻
    ends[-1] = total

    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video.html")
    html = open(p, encoding="utf-8").read()
    it = iter(range(len(SCENES)))
    def sub(m):
        i = next(it)
        return f'data-start="{starts[i]}" data-end="{ends[i]}"'
    html = re.sub(r'data-start="[\d.]+" data-end="[\d.]+"', sub, html)
    caps = ",\n".join(f'  [{starts[i]+0.2:.2f}, {ends[i]-0.1:.2f}, "{c}"]'
                      for i, (_, c, _) in enumerate(SCENES))
    html = re.sub(r"const captions = \[.*?\n\];", f"const captions = [\n{caps},\n];", html, flags=re.S)
    html = re.sub(r"const DURATION = [\d.]+;", f"const DURATION = {total};", html)
    open(p, "w", encoding="utf-8").write(html)
    json.dump({"duration": total, "offsets": offsets}, open(os.path.join(out, "timing.json"), "w"))
    print("total", total)

if __name__ == "__main__":
    main()
