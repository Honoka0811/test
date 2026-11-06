# 卵かけごはんが「ふわとろ10倍」になる裏ワザ — 料理ショート動画

YouTube ショート向けの縦型動画(1080×1920 / 30fps / 約40秒)。
白身だけを先に熱々ごはんに混ぜてメレンゲ状にし、黄身を後からのせる定番の裏ワザを、
問いかけ型フック → 3ステップ → ご褒美カット(黄身を崩す) → コメント/保存誘導、の流れで見せる構成です。
ナレーションは **VOICEVOX:四国めたん**(ノーマル)、BGM と効果音は numpy で自作した権利フリーのものです。

- **アップロード用一式: `upload/`**(最終 mp4・字幕 SRT・サムネイル JPG・タイトル/説明文/タグ/運用メモの `metadata.md`)
- 完成動画: `output/fuwatoro_tkg.mp4`(正規化前)。無音版 `output/video.mp4` は `node capture.js` で再生成(リポジトリには含めない)
- 音声素材: `output/narration.wav`(ナレーション)/ `output/bgm.wav`(BGM)
- ナレーション原稿: `narration_script.txt`(タイムコード付き)

## 構成(約40秒)

| 時間 | シーン | 演出 |
|---|---|---|
| 0:00–0:05 | フック | 「まだ普通に混ぜてる？」巨大テロップ、卵が落ちてバウンド、赤フラッシュ+画面シェイク+「損」スタンプ |
| 0:05–0:10 | 約束 | 「ふわとろ ×10倍」のドンッと出る見出し、キラキラ、「30秒で完成」バッジ、BGM ドロップ |
| 0:10–0:14 | STEP 1 | 卵がひび割れて左右に開き、黄身と白身が別々の小鉢に落ちる |
| 0:14–0:22 | STEP 2 | 白身を注ぐ → 箸がぐるぐる回り泡が増える → 30秒タイマー高速カウントダウン → 「ここが最重要！」「成功！」 |
| 0:22–0:29 | STEP 3 | くぼみ → 黄身がポンと落ちて潰れて戻る → 醤油3滴(1滴ずつカウント) → バターがじゅわ〜と溶ける |
| 0:29–0:34 | ご褒美 | ズームイン、箸で黄身を崩すと黄金色が流れ出す、「ふわっ」「とろっ」が弾む、BGM ブレイク |
| 0:34–0:40 | CTA | コメント/保存ボタンがバウンド、クレジット表示、BGM 再ドロップ |

共通の演出: シーン切り替えごとの白フラッシュ+ズームパンチ、各テロップのポップイン(バウンス)+効果音、
黄色ハイライト付き袋文字テロップ(ナレーションのフレーズ単位で同期)、上部プログレスバー、ゆっくり寄るケンバーンズ。

## 再生成の方法

```bash
cd fuwatoro-tkg-shorts
python3 narrate.py     # ナレーション合成 → output/narration.wav, timeline.json(.js), subtitles_ja.srt
node capture.js        # 無音動画 → output/video.mp4(timeline に合わせて描画)
python3 mix.py         # BGM + 効果音 + ナレーションをミックスして output/fuwatoro_tkg.mp4
node capture.js --thumb                 # サムネイル → output/thumbnail.png
./export_upload.sh     # upload/ にアップロード用一式(-14 LUFS 正規化・ステレオ AAC・SRT・JPG)
node capture.js --stills 1,3.5,10       # 指定秒の静止画で演出を確認(output/stills/)
```

- `narrate.py` … 原稿(`SCENES`)をフレーズごとに VOICEVOX で合成。フレーズの実尺からシーンの開始/終了を決め、タイムラインを書き出す。原稿を書き換えて再実行すれば、映像と音声が自動で追従する
- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)。`output/timeline.js` を読んでテロップとシーンを同期
- `capture.js` … Playwright(Chromium)で 1 フレームずつ撮影し、ffmpeg(libx264)にパイプして mp4 化
- `bgm.py` … 124BPM・Cメジャー(I-V-vi-IV)のアップテンポな BGM(4つ打ち+クラップ+ハット+シンセベース+プラックコード+ペンタトニックのリード+サイドチェイン)。シーンの開始時刻に合わせてイントロ→ドロップ→ブレイク→再ドロップと展開
- `sfx.py` … ウーシュ、ポップ、卵の割れる音、混ぜる音、ポン、醤油のぴちょん、バターのじゅわ、キラキラ、スタンプなどを合成
- `mix.py` … ナレーション中は BGM を自動で下げ(ダッキング)、効果音をタイムラインに沿って配置して動画に合成
- `dsp.py` … 共通の DSP ユーティリティ(FFT フィルタ、リバーブ、ディレイなど)
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、Python 3 + `numpy` + `voicevox_core`、日本語フォント(同梱)

### VOICEVOX のセットアップ(ナレーション用)

VOICEVOX CORE の GitHub リリースから次を取得し、環境変数でパスを渡します。

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| Python ラッパー `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| ONNX Runtime `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| 音声モデル `0.vvm`(四国めたん・ずんだもん ほか) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 `open_jtalk_dic_utf_8-1.11` | open-jtalk (SourceForge) | `VOICEVOX_DICT` |

スタイルを変える場合は `VOICEVOX_STYLE=0 python3 narrate.py`(0 = あまあま、6 = ツンツン、4 = セクシー)。話速は `VOICEVOX_SPEED=1.1` のように指定します。
VOICEVOX の音声を公開する場合は、利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要です(動画の最後のカードと `upload/metadata.md` の説明文に記載済み)。

### フォント

`fonts/` に同梱(いずれも SIL Open Font License 1.1): Dela Gothic One(見出し)、Noto Sans JP Black(テロップ)、M PLUS 1p Black(予備)。絵文字はシステムの Noto Color Emoji を使用。
