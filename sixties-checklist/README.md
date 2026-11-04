# 60代のうちにやっておくべきこと10選 — ショート動画

明るいイラスト多めでテンポよく進む縦型ショート動画(1080×1920 / 30fps / 66.6秒)です。
ナレーションは VOICEVOX の **四国めたん**、BGM はヴィヴァルディ「四季」より「春」(パブリックドメイン)の冒頭テーマを、ビート入りの明るいポップ・クラシック風に自作アレンジしたものです(GeneralUser GS SoundFont で演奏)。

- **アップロード用一式: `upload/`**(最終mp4 -14 LUFS 正規化済み・字幕SRT・サムネイルJPG)
- 完成動画: `output/sixties_checklist.mp4`
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.png`
- ナレーション原稿: `narration_script.txt`

## 構成(66.6秒)

| 時間 | シーン | 画面の見出し / サブ |
|---|---|---|
| 0:00–0:04.6 | タイトル | 60代のうちに やっておくべきこと 10選 |
| 0:04.6– | 01 | 体のメンテナンス / 健診は毎年・歯科検診は半年ごと |
| 0:10.2– | 02 | 筋肉貯金 / 1日20分のウォーキング |
| 0:15.8– | 03 | お金の棚卸し / 年金と資産をまず把握する |
| 0:21.4– | 04 | 持ち物を減らす / 元気なうちに生前整理 |
| 0:27.0– | 05 | エンディングノート / もしもの時の希望を書き残すノート |
| 0:32.6– | 06 | 行きたい場所へ / 動けるうちが旅のベストシーズン |
| 0:38.2– | 07 | 新しい趣味・学び / 始めるのに遅すぎることはない |
| 0:43.8– | 08 | 人とのつながり / 仲間はこれからの大きな財産 |
| 0:49.4– | 09 | 住まいの見直し / 手すり・段差・住み替えは早めに |
| 0:55.0– | 10 | 大切な人との時間 / 「ありがとう」は言えるうちに |
| 1:00.6–1:06.6 | 締め | 全部やらなくてOK。気になった1つから今日はじめてみませんか + 10項目のチェックリスト + クレジット |

各項目は 5.6 秒。番号 → イラスト → 絵文字のポップイン → 見出しカードの順にテンポよく出し、シーン間は横スライドで切り替えます。

## 使用素材とライセンス

| 素材 | 出典 | ライセンス / 表記 |
|---|---|---|
| ナレーション | VOICEVOX:四国めたん(ノーマル) | 利用規約に従い「VOICEVOX:四国めたん」をクレジット表記(動画末尾に記載済み) |
| シーンイラスト | [unDraw](https://undraw.co)(npm `undraw-svg` 経由) | MIT。アクセント色を項目ごとに差し替えて使用 |
| 絵文字イラスト | Microsoft Fluent Emoji(npm `@iconify-json/fluent-emoji` 経由) | MIT |
| フォント | Zen Maru Gothic(npm `@fontsource/zen-maru-gothic` 経由) | SIL OFL 1.1 |
| BGM | ヴィヴァルディ「春」冒頭テーマを `bgm.mjs` で自作アレンジし、[GeneralUser GS](https://schristiancollins.com/generaluser.php) SoundFont(npm `generaluser`)+ [SpessaSynth](https://github.com/spessasus/spessasynth_core) で演奏 | 楽曲はパブリックドメイン。GeneralUser GS は商用含め自由に利用可(ライセンス同梱) |

> この環境では写真素材サイト(Unsplash / Pexels / Wikimedia など)に接続できなかったため、写真の代わりにフラットイラスト+立体絵文字で構成しています。
> 写真に差し替える場合は `render.html` の `ITEMS[].illust` を画像に置き換えてください(`drawImageFit` でそのまま描画できます)。

## 再生成の方法

```bash
cd sixties-checklist
python3 build_assets.py     # assets/illust, assets/emoji の SVG を assets/svgs.js に埋め込む(素材を変えたときだけ)
node capture.js             # output/sixties_checklist_silent.mp4(無音版)を生成
python3 narrate.py          # ナレーション合成 + BGM ミックス → output/sixties_checklist.mp4
npm install                 # BGM 用(SoundFont と JS シンセ)
node bgm.mjs 66.6 output/bgm.wav  # BGM を書き出す(narrate.py が無ければ自動実行)
./export_upload.sh          # upload/ にアップロード用一式を書き出す(-14 LUFS 正規化・AAC・SRT・JPG)
node frames.js out 1.0 9.0  # 指定秒のフレームを PNG で確認
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画。ブラウザで開くとプレビュー再生
- `capture.js` … Playwright(Chromium)で 1 フレームずつ撮影し、ffmpeg(libx264)にパイプして mp4 化
- `bgm.mjs` … 「春」の冒頭テーマ(3 小節 + エコー)を軸に、イントロ → A(テーマ)→ B(16 分音符の走句)→ A → ブリッジ → A → 終止 の 34 小節・119BPM で構成。ストリングス(旋律)、ピアノ、ベース、弦パッド、ピチカート、グロッケン、ドラム(キック・スネア・ハイハット・シェイカー)を MIDI で打ち込み、GeneralUser GS SoundFont を SpessaSynth でオフライン演奏して WAV 化。`output/bgm.mid` も同時に出力
- `narrate.py` … 原稿を VOICEVOX(四国めたん, style 2)で合成し、各シーンに収まるよう話速を自動調整(基準 1.2 倍)。BGM はナレーション中に自動で音量を下げて(ダッキング)ミックス。SRT も同時に生成
- 必要なもの: Node.js + `playwright`(Chromium)+ `npm install`(spessasynth_core, generaluser)、`ffmpeg`、Python 3 + `numpy` + `pyopenjtalk`(辞書用)+ `voicevox_core`

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| 音声モデル `0.vvm`(四国めたん・ずんだもん ほか) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | `pyopenjtalk` が初回に自動取得 | `VOICEVOX_DICT`(任意) |

話し方を変える場合は `VOICEVOX_STYLE=0 python3 narrate.py`(0 = あまあま、6 = ツンツン)のようにします。
