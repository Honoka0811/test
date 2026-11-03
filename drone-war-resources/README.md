# 次世代戦争の勝敗を決める5つの資源と、そのボトルネック — YouTube 解説動画

AIドローン消耗戦の時代に勝敗を左右する5つの資源(半導体・電力・ドローン生産・宇宙インフラ・データと人材)について、
「代替の利かない工程」を公開情報で確認しながら整理する横型動画(1920×1080 / 30fps / 約6分40秒)です。
ナレーションは男性音声(VOICEVOX:青山龍星)、BGMは自作(プログラム合成)です。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグの `metadata.md`)
- 完成動画: `output/drone_war_resources_narrated.mp4`
- ナレーション音声のみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`
- シーンとビートのタイミング: `output/timing.json`(ナレーションの長さから自動生成)
- 事実確認メモと出典: `sources.md`
- 原稿(字幕表記): `narration_script.txt`

## 構成

| シーン | 内容 |
|---|---|
| 導入 | 問いの提示 |
| 前提 | ウクライナ 年産約400万機 / ロシア シャヘド型 月約2,700機 / 5つの資源 |
| 01 半導体 | EDA(3社74%)/ EUV(ASML 1社)/ 先端ファブ / CoWoS+HBM(上位4社が90%超)/ 材料 / ドローン側は成熟プロセスで足りる |
| 02 電力 | ガスタービン受注残 116/69/32 GW / 変圧器 平均128週 / 濃縮はロシア約4割・HALEU / 太陽電池・電池材料 / 送電網は標的 |
| 03 ドローン生産 | 磁石 中国94% / 電池セル / 熱画像 / 炭素繊維 / 炸薬(NC・TNT・RDX)/ 光ファイバー |
| 04 宇宙インフラ | 海上ドローン×スターリンク / 端末 1.1kg・25〜40W / SpaceX 80%超 / 千帆・国網 / 停止権限 |
| 05 データと人材 | 収集・更新・制度 |
| まとめ | 米国・中国・欧州日本・中堅国の急所 / 核抑止という天井 |

## 再生成の方法

```bash
cd drone-war-resources
./build.sh                 # 下の4段階をまとめて実行
# 個別に:
python3 narrate.py         # ナレーション合成 → output/narration.wav, timing.json, subtitles_ja.srt
node capture.js            # timing.json に従って映像を描画 → output/video_silent.mp4, thumbnail.png
python3 mix.py             # BGM 生成 + ダッキングしてミックス → output/drone_war_resources_narrated.mp4
./export_upload.sh         # upload/ に -14 LUFS 正規化した最終版・SRT・サムネイルを書き出す
node preview.js 12 75 150  # 指定秒のフレームを output/preview/ に書き出す(レイアウト確認用)
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)。シーンの尺は `setTiming()` で受け取る
- `narrate.py` … 原稿(`SCRIPT`)をビート単位で VOICEVOX(話者: 青山龍星 ノーマル, style 13)で合成し、ナレーションの長さからシーンの尺を決める。読み上げ用テキストは英字略語をカタカナ、数値を漢数字にして読み間違いを避けている
- `bgm.py` … テック系ドキュメンタリー風BGM(Eマイナー、84BPM。脈動ベース+倍音パッド+柔らかいキック+まばらなプラック+簡易リバーブ)を numpy だけで合成
- `mix.py` … ナレーション中は BGM を自動で下げて(ダッキング)ミックスし、動画に合成
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、日本語フォント(IPAゴシック)、Python 3 + `numpy` + `voicevox_core` + `pyopenjtalk`(辞書用)

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(`lib/libvoicevox_onnxruntime.so`) |
| `15.vvm`(青山龍星) | VOICEVOX/voicevox_vvm releases(0.17.1) | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | `pyopenjtalk` 初回実行時に自動取得 | `VOICEVOX_DICT`(任意) |

VOICEVOX の音声を公開する場合は、利用規約に従い「VOICEVOX:青山龍星」のクレジット表記が必要です(エンドカードと説明文に記載済み)。

## ショート版(`short/`)

同じ内容を59秒の縦型(1080×1920)にまとめたショート動画。構成は 導入 → 5資源×各2枚のカード → まとめ → エンドカード。
`short/narrate.py` は合計が59秒に収まるまで話速を自動で上げる(最終 1.19 倍)。
再生成は `cd short && python3 narrate.py && node capture.js && python3 mix.py && ./export_upload.sh`。
アップロード用一式は `short/upload/`(mp4・SRT・サムネイル・`metadata.md`)。
