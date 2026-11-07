# 脳卒中の見分け方「FAST」— YouTube ショート動画(医療)

家族が急にろれつが回らなくなったとき「様子を見る」が最悪の選択である理由と、脳卒中のサインを見抜く4文字「FAST」を、
縦型ショート動画(1080×1920 / 30fps / 約68秒)にまとめたものです。ナレーションは VOICEVOX:四国めたん。

- **アップロード用一式: `upload/`**(最終 mp4・字幕 SRT・サムネイル JPG・タイトル/説明文/タグ/チェックリストの `metadata.md`)
- 完成動画: `output/stroke_fast.mp4`(`upload/stroke_fast_final.mp4` は -14 LUFS 正規化済み)
- ナレーション音声: `output/narration.wav` / BGM: `output/bgm.wav` / 効果音: `output/sfx.wav`
- 原稿: `narration_script.txt`

## 構成と演出(約68秒)

| 時間 | シーン | 演出 |
|---|---|---|
| 0:00–0:07 | 緊急クイズ | 心電図の脈動+心音、3択カードがスライドイン、2.7秒のカウントダウンバーとティック音 |
| 0:07–0:14 | 正解発表 | 「正解!」バースト、不正解に赤×、「最悪の選択」の赤スタンプが画面揺れとともに叩き込まれる |
| 0:14–0:21 | 衝撃の数字 | 脳の神経細胞ドットが赤く光って消えていき、カウンターが 0 → 1,900,000 まで駆け上がる |
| 0:21–0:25 | FAST | ライザー音からの F・A・S・T タイル 4 連スラム+フラッシュ |
| 0:25–0:30 | F = Face | 顔イラストの片側がゆっくり垂れ下がる、警告音と赤矢印 |
| 0:30–0:35 | A = Arm | 棒人間の片腕だけが落ちていく |
| 0:35–0:41 | S = Speech | 吹き出しの文字が震えて崩れる |
| 0:41–0:48 | T = Time | 「119」のパルス+アラーム、発症時刻のメモカード |
| 0:48–0:55 | 4.5 時間 | 減っていくリング、t-PA のピル、「TIME IS BRAIN」 |
| 0:55–1:01 | やってはいけない3つ | 3連赤×スタンプ |
| 1:01–1:08 | CTA | 保存ブックマークのバウンス、FAST おさらい、クレジット・注記 |

字幕は行ごとに「ポップ」して表示され、キーワード(119番・190万個・4.5時間 など)を黄色で強調しています。
BGM は 128BPM・D マイナーの四つ打ち(シーンごとに強度が変化し、クイズ中は控えめ、FAST 解説で最大、NG で一度落として CTA で再び上がる)。
ナレーション中は自動で音量を下げるダッキング付き。BGM・効果音はすべて numpy で合成しているため権利表記は不要です。

## 医学的な根拠(動画内の数字)

| 内容 | 出典 |
|---|---|
| 脳卒中では治療が 1 分遅れるごとに約 190 万個の神経細胞が失われる | Saver JL. "Time is brain—quantified." *Stroke*. 2006;37:263-266 |
| FAST(Face / Arm / Speech / Time)による見分け方 | 日本脳卒中協会「ACT FAST」キャンペーン、American Stroke Association |
| 発症から 4.5 時間以内であれば rt-PA(アルテプラーゼ)静注療法の適応になりうる | 日本脳卒中学会『rt-PA(アルテプラーゼ)静注療法 適正治療指針』 |
| 飲食物を与えない(誤嚥の危険)、自家用車で搬送せず救急車を呼ぶ、発症時刻を記録する | 日本脳卒中協会ほか救急啓発資料 |

動画末尾に「※一般的な情報です。症状があれば迷わず119番・医療機関へ」の注記を入れています。

## 再生成の方法

```bash
cd stroke-fast-short
python3 narrate.py                 # VOICEVOX(四国めたん)でナレーション合成 → output/narration.wav, timeline.json, subtitles_ja.srt
python3 audio.py                   # 演出イベント算出 → events.json、BGM/SFX 合成 → mix.wav
node capture.js output/stroke_fast_silent.mp4   # Playwright で 1 フレームずつ撮影(無音)
python3 mux.py                     # 音声を合成 → output/stroke_fast.mp4
node capture.js --thumb            # サムネイル → output/thumbnail.png
./export_upload.sh                 # upload/ に -14 LUFS 正規化版・SRT・JPG を書き出す
```

- `script.py` … シーン構成とナレーション原稿(読み上げ用テキストと画面字幕テキストを別々に持つ)
- `narrate.py` … 行ごとに VOICEVOX で合成し、実際の音声長からシーンの開始・終了時刻を決めて `timeline.json` に書く(映像は音声に合わせて伸縮する)
- `events.py` … タイムラインから演出イベント(スタンプ・スラム・カウントダウン等)の時刻を算出。映像と音の両方がこれを参照するので同期がずれない
- `audio.py` … BGM・効果音の合成とダッキングミックス
- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)
- `capture.js` … Playwright(Chromium)で撮影し ffmpeg(libx264)にパイプ
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、Python 3 + `numpy` + `scipy` + `voicevox_core`、フォント `Noto Sans CJK JP`(`fonts-noto-cjk`)

### VOICEVOX のセットアップ

VOICEVOX CORE の GitHub リリースから取得し、環境変数でパスを渡します。

| 必要なもの | 取得元 | 環境変数(既定値) |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(`/home/user/vv/ort/.../lib/libvoicevox_onnxruntime.so`) |
| `0.vvm`(四国めたん・ずんだもん等) | VOICEVOX/voicevox_vvm releases 0.17.1 | `VOICEVOX_VVMS`(`/home/user/vv/vvms`) |
| `open_jtalk_dic_utf_8-1.11.tar.gz` | r9y9/open_jtalk releases | `VOICEVOX_DICT`(`/home/user/vv/dict/open_jtalk_dic_utf_8-1.11`) |

話者は `VOICEVOX_STYLE=2`(四国めたん ノーマル)が既定。0 = あまあま、6 = ツンツン、4 = セクシー。
VOICEVOX の音声を公開する場合は利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要です(動画末尾と説明文に記載済み)。
