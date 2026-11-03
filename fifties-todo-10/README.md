# 50代のうちにやっておくべきこと10選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約77秒)。イラスト(写真カード風)多めのテンポ重視の構成で、
ナレーションは VOICEVOX の **四国めたん**、BGM はバッハ「平均律クラヴィーア曲集 第1番 プレリュード(BWV 846)」の自作アレンジです。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグ/チェックリストの `metadata.md`)
- **YouTube への投稿**: `upload/upload_youtube.py`(YouTube Data API で動画・字幕・サムネイルをまとめて投稿。手順と手動投稿の方法は `upload/metadata.md`)
- 完成動画: `upload/fifties_todo_10_final.mp4`
- 中間生成物(`output/`): `subtitles_ja.srt`、`timeline.json`、`thumbnail.png`(正規化前の mp4 や wav は再生成できるため未コミット)

## 構成(約77秒)

| # | 項目 | 一言 |
|---|---|---|
| — | タイトル | 50代のうちに やっておくべきこと 10選 |
| 1 | 人間ドックで体の棚卸し | 年に1回、しっかりチェック |
| 2 | 筋トレで「筋肉貯金」 | スクワット＋ウォーキング |
| 3 | 歯のメンテナンス | 3か月に1回はクリーニング |
| 4 | お金の見直し | 年金・保険・資産をまとめて把握 |
| 5 | 親と「これから」を話す | 介護・住まい・お金のこと |
| 6 | モノを減らす | 使っていない物は手放す |
| 7 | 新しいことを学ぶ | 資格・語学・スマホでもOK |
| 8 | 仕事以外の居場所をつくる | 肩書きなしで付き合える人を |
| 9 | 家族との時間を予定に入れる | 後回しにせずカレンダーへ |
| 10 | 60代からのやりたいことリスト | 小さなことからでOK |
| — | まとめ | まずは1つ、今日から。 |

各シーンの長さはナレーションの実測長から自動で決まります(`output/timeline.json`)。

## 再生成の方法

```bash
cd fifties-todo-10
python3 narrate.py          # ナレーション合成 → output/timeline.json, narration.wav, bgm.wav, mix.wav, subtitles_ja.srt
node capture.js             # timeline.json に従って output/fifties_todo_10.mp4(無音)を生成
./export_upload.sh          # 音声を合成し -14 LUFS に正規化、upload/ に一式を書き出す
python3 bgm.py 77 bgm.wav   # BGM だけを書き出す場合
node capture.js --frames 2.6,10.0 output/frames   # 指定秒のフレームを PNG で確認
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画。ブラウザで開くとプレビュー再生(ローカル画像を読むため Chromium は `--allow-file-access-from-files` 付きで起動)
- `capture.js` … Playwright(Chromium)で 1 フレームずつ撮影し、ffmpeg(libx264)にパイプして mp4 化
- `bgm.py` … バッハ「平均律クラヴィーア曲集 第1番 プレリュード(BWV 846)」のアレンジを numpy だけで合成(64BPM。原曲どおりの分散和音をハープ/ピアノ風の撥弦音で + 薄い弦パッド + 低音 + 軽いリバーブ)。原曲はパブリックドメイン、音源も自作のため権利表記は不要
- `narrate.py` … 原稿を VOICEVOX(四国めたん ノーマル, style 2, 話速 1.28)で合成し、BGM をナレーション中に自動で音量を下げて(ダッキング)ミックス
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、Python 3 + `numpy` + `pyopenjtalk` + `voicevox_core`

### 素材とライセンス

| 素材 | 出所 | ライセンス / 表記 |
|---|---|---|
| イラスト `assets/emoji/*.svg` | [Twemoji](https://github.com/twitter/twemoji) | CC-BY 4.0(動画末尾と説明文にクレジット) |
| フォント `assets/fonts/MPLUSRounded1c-*.ttf` | [M PLUS Rounded 1c](https://github.com/google/fonts/tree/main/ofl/mplusrounded1c) | SIL Open Font License 1.1 |
| ナレーション | VOICEVOX 四国めたん | 利用規約に従い「VOICEVOX:四国めたん」を表記(動画末尾・説明文) |
| BGM | 自作(`bgm.py`) | 表記不要 |

写真素材サイト(Unsplash / Pexels / Wikimedia Commons など)は制作環境のネットワークから到達できなかったため、
写真の代わりに Twemoji のイラストを「写真カード」風(白フチ+影+傾き)に見せる演出にしています。

### VOICEVOX のセットアップ(ナレーション用)

VOICEVOX CORE の GitHub リリースから次を取得し、環境変数でパスを渡します。

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| Python ラッパー `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| ONNX Runtime `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| 音声モデル `0.vvm`(四国めたん・ずんだもん ほか) | VOICEVOX/voicevox_vvm releases(tag 0.17.1) | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | `pyopenjtalk` 同梱のものを自動使用 | `VOICEVOX_DICT`(任意) |

話者スタイルを変える場合は `VOICEVOX_STYLE=0 python3 narrate.py`(0 = あまあま、6 = ツンツン、4 = セクシー)のようにします。
原稿は `narrate.py` の `SCRIPT`(読み上げ用。読み間違いを避けるため一部ひらがな)と `SUBTITLES`(表示用)、
`render.html` の `SUBTITLES` にあり、三つを揃えて書き換えます。
