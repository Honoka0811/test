"""乱数放送ショート：台本・演出データ

text    : VOICEVOX に読ませる文（読み間違い対策でカタカナ表記を混ぜている）
caption : 画面に出すテロップ。【】で囲んだ部分が強調色になる
style   : 四国めたんのスタイル（normal=ノーマル / whisper=ささやき / hiso=ヒソヒソ）
visual  : render.py の演出ID
"""

SCENES = [
    dict(id="hook1", style="whisper", visual="radio",
         text="深夜のラジオから、謎の数字が聞こえてきたら……",
         caption="深夜のラジオから\n謎の【数字】が\n聞こえてきたら…"),
    dict(id="hook2", style="normal", visual="radio_alert",
         text="それは、スパイへの暗号指令かもしれません。",
         caption="それは\n【スパイへの暗号指令】\nかもしれない"),
    dict(id="title", style="normal", visual="title",
         text="乱数放送。短波ラジオで、ただ数字を読み上げ続ける、正体不明の放送です。",
         caption="短波ラジオで\n数字を読み上げ続ける\n【正体不明の放送】"),
    dict(id="coldwar", style="normal", visual="telegram",
         text="冷戦時代、各国の諜報機関が、敵国に潜む工作員へ、指令を送るために使ったと言われています。",
         caption="冷戦時代\n諜報機関が【工作員】へ\n指令を送っていた"),
    dict(id="otp", style="normal", visual="otp",
         text="使われたのは、ワンタイムパッド。受信者だけが持つ乱数表を使えば、理論上、絶対に解読できない暗号になります。",
         caption="【ワンタイムパッド】\n乱数表がなければ\n理論上 解読不能"),
    dict(id="uvb", style="normal", visual="buzzer",
         text="中でも有名なのが、ロシアの、ユーブイビー・ナナロク。通称、ザ・バザー。何十年も、不気味なブザー音を鳴らし続けています。",
         caption="ロシアの【UVB-76】\n通称「ザ・バザー」\n何十年も鳴り続ける"),
    dict(id="words", style="whisper", visual="redacted",
         text="そして時々……謎の言葉が、読み上げられるんです。",
         caption="そして時々…\n【謎の言葉】が\n読み上げられる"),
    dict(id="nk", style="normal", visual="year",
         text="北朝鮮のピョンヤン放送も、2016年、16年ぶりに乱数放送を再開して、ニュースになりました。",
         caption="北朝鮮も2016年\n【16年ぶり】に\n乱数放送を再開"),
    dict(id="now", style="normal", visual="radar",
         text="そして今も……乱数放送は、世界のどこかで、流れ続けています。",
         caption="そして今も\n世界のどこかで\n【流れ続けている】"),
    dict(id="hidden", style="hiso", visual="hidden",
         text="……実はこの動画にも、4つの数字を隠しました。全部見つけたら、コメントで教えてください。",
         caption="この動画にも\n【4つの数字】を隠した\n見つけたらコメントへ"),
]

# 隠し数字（シーン番号, シーン開始からの秒, 数字, 中心座標）
# 答えは 4・6・2・5 ＝ UVB-76 の周波数 4625kHz（後半で回収される伏線）
HIDDEN = [
    (0, 1.6, "4", (860, 520)),
    (2, 2.2, "6", (210, 980)),
    (3, 3.0, "2", (880, 1040)),
    (4, 1.4, "5", (190, 470)),
]
HIDDEN_FRAMES = 4  # 30fpsで約0.13秒。一時停止で探せる長さ

# 4625kHz で固定され始めるシーン
FREQ_LOCK_SCENE = "uvb"
