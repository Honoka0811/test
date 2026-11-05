# オススメのストレス解消法 TOP10 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約75秒)。ナレーションは **VOICEVOX:四国めたん**、BGM と効果音はプログラムで自作したもの(権利フリー)です。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグの `metadata.md`)
- 音量正規化前の完成動画: `output/stress_relief_top10.mp4`(再生成で作られる。リポジトリには含めない)
- ナレーションのみ `output/narration.wav` / BGMのみ `output/bgm.wav` / タイミング `output/timeline.json`

## 構成と演出

| 時間 | シーン | 視聴者を引きつける工夫 |
|---|---|---|
| 0:00–0:08 | フック | 1フレーム目から「ストレス」と震える顔を表示 → タイトルコール「TOP10」 → 「1位は、みんなが後回しにしてる、アレ！」と鍵付きの「？」で最後まで見る理由をつくる |
| 0:08–0:42 | 10位〜4位 | 順位がスラム(拡大→着地)・衝撃波・画面シェイク・効果音。ワイプで切り替え、絵文字カードはビートに合わせて脈打つ。上部の進行チップで残りの数が分かる |
| 0:42–0:45 | TOP3 突入 | フラッシュと金色の「TOP3」、メダル、ライザーとスネアロールで盛り上げる |
| 0:45–0:57 | 3位・2位 | 2位で四国めたん(ツンツン)が「今これ見てるあなたも、だからね？」とツッコミ(吹き出し＋ズーム) |
| 0:57–1:01 | 1位の前 | BGMを止めてドラムロール。スポットライトと震える「？」 |
| 1:01–1:07 | 1位 | 白フラッシュ・紙吹雪・王冠。BGMが再び盛り上がる。「今夜は、早めに寝ようね」はあまあま声 |
| 1:07–1:15 | まとめ | 10個の一覧と「保存して」「コメントで教えてね」(エンゲージメントを促す) |

- 字幕は句読点ごとに切り替え、数字やキーワードを黄色で強調。表示のタイミングは VOICEVOX の音素長から算出
- 各シーンの開始は BGM の拍(120BPM)にそろえている
- 下端 300px と右端は Shorts の UI と重ならないように空けている

## BGM(`bgm.py`)
120BPM・ハ長調・**王道進行(F△7→G→Em7→Am)** のポップ曲。4つ打ちキック、クラップ、裏拍のハイハット、ベース、サイドチェインのかかったパッド、16分のアルペジオ、リードのフック。
イントロ → ドロップ(10位) → TOP3前のビルド → 再ドロップ(3位) → ブレイク(1位の前) → 最後のドロップ(1位) → アウトロ、とタイムラインに合わせて展開します。
ナレーション中は自動で BGM の音量を下げ(ダッキング)、最終的に -14 LUFS に正規化します。

## 再生成の方法

```bash
cd stress-relief-top10
python3 narrate.py      # ナレーション合成 → output/narration.wav, timeline.json/js, subtitles_ja.srt
node capture.js --thumb # サムネイル output/thumbnail.png
node capture.js         # 映像(無音) output/video_silent.mp4  ※約9分
python3 mix.py          # BGM・効果音・ナレーションをミックスして output/stress_relief_top10.mp4
./export_upload.sh      # upload/ に最終版(-14 LUFS)を書き出し
node capture.js --stills 3.8 44 62   # 確認用の静止画を output/stills/ に保存
```

`render.html` をブラウザで直接開くとプレビュー再生できます(音声なし)。原稿は `narrate.py` の `SCENES`、各項目の表示内容は `render.html` の `ITEMS` にあります。

必要なもの: Node.js + playwright(Chromium)、ffmpeg、Python 3 + numpy + scipy、`fonts/` のフォント、Noto Color Emoji。

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数(既定値は `/home/user/vv/...`) |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT` |
| 音声モデル `0.vvm`(四国めたん) | VOICEVOX/voicevox_vvm releases (0.17.1) | `VOICEVOX_VVMS` |
| `open_jtalk_dic_utf_8-1.11.tar.gz` | r9y9/open_jtalk releases (v1.11.1) | `VOICEVOX_DICT` |

使用スタイル: 四国めたん ノーマル(2) / あまあま(0) / ツンツン(6)。
VOICEVOX の音声を公開する際は「VOICEVOX:四国めたん」のクレジット表記が必要です(動画の最後と説明文に記載済み)。
