# 日本三大○○ 10連発 — ショート動画

「日本三大祭り」「日本三景」「日本三名園」…といった **日本三大○○を10個、テンポよく紹介する縦型ショート動画**(1080×1920 / 30fps / 60秒)です。
各カテゴリで3つの名所がカード形式で順に現れ、下部の日本地図に番号付きのピンが打たれます。男性音声のナレーションと自作BGM付き。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグ/投稿手順の `metadata.md`・API投稿用の `youtube.json`)
- YouTube への投稿: 手順は `upload/metadata.md`。`youtube_upload.py` で YouTube Data API から投稿することもできます(動画+サムネイル+字幕)
- 完成動画(ナレーション付き): `output/nihon_sandai_narrated.mp4`
- 完成動画(無音・字幕なし): `output/nihon_sandai.mp4`
- ナレーション音声のみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`(自作・権利フリー)
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.png`

## 構成(60秒)

| 時間 | シーン | 3つ | 補足 |
|---|---|---|---|
| 0:00–0:03.6 | タイトル | 「日本三大○○ 10連発」 | ○○がカテゴリ名に次々入れ替わる |
| 0:03.6 | 1. 日本三大祭り | 祇園祭(京都)・天神祭(大阪)・神田祭(東京) | |
| 0:08.9 | 2. 日本三景 | 松島(宮城)・天橋立(京都)・宮島(広島) | |
| 0:14.2 | 3. 日本三名園 | 兼六園(金沢)・偕楽園(水戸)・後楽園(岡山) | |
| 0:19.5 | 4. 日本三大夜景 | 函館・神戸・長崎 | |
| 0:24.8 | 5. 日本三名城 | 名古屋城・大阪城・熊本城 | ※諸説あり(姫路城を入れる説も) |
| 0:30.1 | 6. 日本三名泉 | 草津温泉(群馬)・下呂温泉(岐阜)・有馬温泉(兵庫) | |
| 0:35.4 | 7. 日本三名瀑 | 華厳の滝(栃木)・那智の滝(和歌山)・袋田の滝(茨城) | |
| 0:40.7 | 8. 日本三大ラーメン | 札幌・喜多方・博多 | |
| 0:46.0 | 9. 日本三大和牛 | 松阪牛(三重)・神戸牛(兵庫)・近江牛(滋賀) | ※諸説あり(米沢牛を入れる説も) |
| 0:51.3 | 10. 日本三大がっかり名所 | 札幌時計台・はりまや橋(高知)・オランダ坂(長崎) | ※諸説あり(守礼門を入れる説も) |
| 0:56.6–1:00 | まとめ | 10カテゴリのおさらい + 「答えはコメントで」 | |

「日本三大○○」は公式な定義があるものではなく、カテゴリによって諸説あります。諸説が特に分かれるものは画面内に「※諸説あり」と明記しています。

## 再生成の方法

```bash
cd nihon-sandai
./build.sh                  # 下の 4 ステップを順に実行
# 個別に実行する場合
python3 narrate.py          # ナレーション合成 + BGM ミックス(output/nihon_sandai.mp4 があれば音声を合成した mp4 も出力)
node capture.js             # output/nihon_sandai.mp4 (無音版) を生成。output/credit.txt があれば末尾のクレジット表記に反映
python3 bgm.py 60 bgm.wav   # BGM だけを書き出す場合
./export_upload.sh          # upload/ にアップロード用一式を書き出す(-14 LUFS 正規化・ステレオAAC・SRT・JPG)
node capture.js --frames 3.0,10,30 output/frames   # 指定秒のフレームを PNG で確認
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)。紹介する項目・ひとこと解説・緯度経度は冒頭の `ITEMS` にまとめてあり、書き換えれば差し替えられます
- `japan_outline.js` … 日本地図の海岸線データ(dataofjapan/land の japan.geojson を Douglas-Peucker で簡略化、沖縄は描画範囲外)
- `capture.js` … Playwright(Chromium)で 1 フレームずつ撮影し、ffmpeg(libx264)にパイプして mp4 化
- `bgm.py` … 明るいトリビア調のBGM(Cメジャー、112BPM。カリンバ風アルペジオ + ベース + 軽いキック/シェイカー/クラップ + 薄いパッド + 簡易リバーブ)を numpy だけで合成。外部音源を使わないため権利表記は不要
- `narrate.py` … シーンごとの原稿を合成し、各シーンの長さに収まるよう話速を自動調整。BGM はナレーション中に自動で音量を下げて(ダッキング)ミックス。固有名詞は読み間違い防止のため原稿をかな書きにしてあり、字幕は漢字表記
- 必要なもの: Node.js, `playwright`(Chromium), `ffmpeg`, 日本語フォント(IPAゴシック)+ Noto Color Emoji, Python 3 + `numpy`

### ナレーションエンジン

`narrate.py` は次の順で使えるものを自動選択します。使ったエンジン名は `output/credit.txt` に書き出され、動画末尾のクレジットに反映されます。

| 優先 | エンジン | 必要なもの | クレジット表記 |
|---|---|---|---|
| 1 | VOICEVOX(青山龍星、style 13) | `voicevox_core` + ONNX Runtime + `15.vvm`(下記) | VOICEVOX:青山龍星 |
| 2 | Open JTalk CLI(nitech-jp-atr503-m001、男性) | `apt install open-jtalk open-jtalk-mecab-naist-jdic hts-voice-nitech-jp-atr503-m001` | Open JTalk |
| 3 | pyopenjtalk | `pip install pyopenjtalk` | Open JTalk |

現在の `upload/` は **VOICEVOX(青山龍星)** で作成しています。VOICEVOX を使うには VOICEVOX CORE の GitHub リリースから次を取得し、既定のパス(`/home/user/vv/...`)以外に置いた場合は環境変数でパスを渡して `./build.sh` を実行してください。

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| Python ラッパー `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| ONNX Runtime `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| 音声モデル `15.vvm`(青山龍星) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | apt の `/var/lib/mecab/dic/open-jtalk/naist-jdic`(あれば自動使用)か pyopenjtalk 同梱のもの | `VOICEVOX_DICT`(任意) |

VOICEVOX の音声を公開する場合は、利用規約に従い「VOICEVOX:青山龍星」のクレジット表記が必要です(動画末尾に自動で入ります)。

ナレーションの原稿は `narrate.py` の `ITEM_SCRIPT`(読み上げ用)と `ITEM_SUB`(字幕用)にあります。
