"""VOICEVOX（四国めたん）でナレーションを生成し、シーン尺を合わせて video.html を更新する。
使い方: python3 narrate.py <作業ディレクトリ>
前提: VOICEVOXエンジンが localhost:50021 で起動していること
  docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
"""
import json, re, sys, wave, urllib.request, urllib.parse, os

HOST = "http://localhost:50021"
SPEAKER = 2  # 四国めたん ノーマル
SPEED = 1.12
LEAD = 0.35   # シーン開始からナレーション開始まで
TAIL = 0.55   # ナレーション終了後の余白

# (ナレーション, 字幕, 最低シーン秒数)
SCENES = [
    ("クロードコード、聞いたことあるかしら？いま話題のAIエンジニアを、わたくしがざっくり解説しますわ。",
     "Claude Code、聞いたことあるかしら？", 4.6),
    ("ひとことで言うと、アンソロピックが作った、AIコーディングエージェント。チャットで答えるだけじゃなく、実際にファイルを編集して、作業を進めてくれますの。",
     "ひとことで言うと<br>自分で手を動かすAIエンジニア", 5.8),
    ("コードを読んで、書いて、コマンドやテストを実行して、ギットのコミットやプルリクエストまで。プロジェクトまるごと任せられますわ。",
     "コードを読む・書く・実行する<br>Git操作までお任せ", 7.0),
    ("使い方はかんたん。ターミナルでクロードと打って、やりたいことを日本語で頼むだけ。調査から修正、テストが通るところまで、自分で進めてくれますの。",
     "日本語で伝えるだけで<br>調査→修正→テストまで自動で", 10.0),
    ("使える場所も自由自在。ターミナルはもちろん、ブイエスコードやジェットブレインズ、デスクトップアプリ、それにウェブやスマホからも使えますわ。",
     "ターミナル・エディタ・アプリ・Web<br>使う場所を選べます", 6.2),
    ("クロードエムディーでプロジェクトのルールを覚えさせたり、エムシーピーで外部ツールとつないだり。コマンドやフックで、作業の自動化もできますの。",
     "ルールの記憶や外部ツール連携で<br>自分好みに拡張できます", 6.8),
    ("それに、大事な操作の前には、ちゃんと許可を求めてくれるから安心。主導権は、いつもあなたにありますわ。",
     "大事な操作の前には<br>ちゃんと許可を求めてくれる", 5.6),
    ("インストールはコマンドひとつ。まずは小さなタスクから、試してみてちょうだい！",
     "まずは小さなタスクから<br>試してみてね！", 5.0),
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
        q["prePhonemeLength"] = 0.05
        q["postPhonemeLength"] = 0.1
        wav = post("/synthesis", {"speaker": SPEAKER}, q)
        path = os.path.join(out, f"n{i}.wav")
        open(path, "wb").write(wav)
        with wave.open(path) as w:
            d = w.getnframes() / w.getframerate()
        dur = max(mindur, LEAD + d + TAIL)
        starts.append(round(t, 2)); offsets.append(round(t + LEAD, 2))
        t += dur; ends.append(round(t, 2))
        print(f"scene{i+1}: {d:.2f}s voice -> {dur:.2f}s scene")
    total = round(t + 0.8, 2)  # 最後に少し余韻
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
