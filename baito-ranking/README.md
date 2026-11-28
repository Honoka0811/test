# やってみたくなるバイトランキング TOP5 — ショート動画

「楽しすぎて時間を忘れる!?」バイトを、ずんだもん × 四国めたんの掛け合いでカウントダウン紹介する
縦型ショート動画(1080×1920 / 30fps / 約68秒)です。ナレーション・自作BGM・効果音・字幕つき。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグ/チェックリストの `metadata.md`)

## 構成(約68秒)

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00–0:06 | オープニング | 「やってみたくなるバイトランキング」+ TOP5 メダル |
| 0:06–0:14 | 第5位 映画館スタッフ 🎬 | 映画が無料で観られる劇場も / ポップコーン / 新作情報 |
| 0:14–0:23 | 第4位 カフェスタッフ ☕ | ラテアート / ドリンク割引 / おしゃれな空間 |
| 0:23–0:33 | 第3位 イベント・ライブスタッフ 🎤 | 1日だけの単発OK / フェスの熱気 / 日払い |
| 0:33–0:43 | 第2位 テーマパークスタッフ 🎢 | お祭り気分 / ゲストの笑顔 / パーク利用特典 |
| 0:43–0:46 | ドラムロール | 暗転+スポットライト、BGM が止まって溜める |
| 0:46–1:00 | 第1位 リゾートバイト 🏝️ | 寮費・光熱費無料の求人 / 食事付き / 温泉・海・スキー / 全国の仲間 |
| 1:00–1:08 | まとめ | 5位までの一覧 + 「コメントで教えてね！」 |

各順位のカードには「楽しさ・稼げる・特典」の星評価(動画内の独自の目安)と、メリット3〜4つが順に出ます。
特典・待遇は求人や店舗で違うので、画面と説明文に「※特典・待遇は求人や店舗によって異なります」と入れています。

## 作り方(再生成)

```bash
cd baito-ranking
python3 voice.py        # 台本を VOICEVOX で合成 → output/voice.wav, output/subtitles_ja.srt, timeline.js/json
node capture.js         # render.html を1フレームずつ撮影 → output/video_silent.mp4
python3 audio.py        # BGM+効果音を合成してナレーションとミックス → output/baito_ranking.mp4
./export_upload.sh      # upload/ に最終mp4(-14 LUFS・ステレオ)・SRT・サムネイルを書き出す
```

確認用: `node capture.js --stills 7.5 47` で指定秒の静止画を `output/stills/` に、ブラウザで
`render.html` を開くとプレビュー再生(`render.html?t=12` で静止)。ローカルサーバ経由で開いてください
(例: `python3 -m http.server` → http://localhost:8000/render.html)。

| ファイル | 役割 |
|---|---|
| `voice.py` | 台本(`SCENES`)。話者・読み上げ文・字幕文・演出マーク(`p0@0.5` = その行の50%地点でメリット0を表示)を持つ。音声の実測長からタイムラインを組むので、台本を書き換えても映像・効果音が自動で追従する |
| `render.html` | Canvas 2D の `render(t)` が時刻 t のフレームを決定論的に描く。職種データは `JOBS`、配色は `THEMES` |
| `capture.js` | Playwright(Chromium)で撮影して ffmpeg(libx264)にパイプ。アイコン入り canvas を書き出せるよう内部で小さな HTTP サーバを立てる |
| `audio.py` | BGM(128BPM・C-G-Am-F のポップ曲。第1位で頭から鳴らし直し)と効果音(シュッ/ドン/ジャン/ポンッ/星/ドラムロール/クラッシュ+ファンファーレ/コイン/キラキラ)を numpy だけで合成。ナレーション中は BGM を自動で下げ(-12dB、無音時 -5dB)、軽いコンプ+リミッターで整える |
| `export_upload.sh` | ラウドネスを計測し、-14 LUFS と True Peak -1dB の範囲で音量だけ調整して upload/ に書き出す |

必要なもの: Node.js + `playwright`(Chromium), `ffmpeg`, Python 3 + `numpy` + `pyopenjtalk`(辞書用)+ VOICEVOX CORE。

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(`lib/libvoicevox_onnxruntime.so`) |
| `0.vvm`(四国めたん・ずんだもん・春日部つむぎ・雨晴はう) | VOICEVOX/voicevox_vvm releases (0.17.1) | `VOICEVOX_VVMS`(置いたディレクトリ) |

話者・話速は `voice.py` の `VOICES`(ずんだもん ノーマル=3 / 四国めたん ノーマル=2)。
読み間違える語は読み上げ用テキストだけかなにする(例: 「日払い」→「ひばらい」。字幕は漢字のまま)。

## 素材とクレジット

- ナレーション: **VOICEVOX:ずんだもん / VOICEVOX:四国めたん**(公開時はクレジット表記が必須。動画のまとめ画面と説明文に記載済み)
- BGM・効果音: `audio.py` で合成した自作音源(権利表記不要)
- 絵文字アイコン: Twemoji(CC-BY 4.0)— `icons/LICENSE.md`
- フォント: Dela Gothic One / M PLUS Rounded 1c(SIL OFL 1.1)— `fonts/OFL-*.txt`
