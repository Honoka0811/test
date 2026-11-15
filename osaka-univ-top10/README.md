# 大阪大学のここがすごい！10選 — ショート動画

大阪大学の「すごいところ」を10位から1位までカウントダウンで紹介する縦型ショート動画(1080×1920 / 30fps / 約102秒)。
ナレーションは **VOICEVOX:四国めたん(ノーマル)**、BGM は numpy で合成したオリジナル曲(権利フリー)。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグの `upload/metadata.md`)
- 原稿: `script.py`(読み上げ用テキストと字幕用テキストのペア)

## 構成

| 順位 | 内容 | 画面のイラスト |
|---|---|---|
| タイトル | 大阪大学のここがすごい！10選 | 10選バッジ・舞うイチョウ |
| 10位 | キャンパスからワニの化石(マチカネワニ、全長約7m、国の天然記念物) | ワニ+定規 |
| 9位 | 手塚治虫が大阪帝国大学附属医学専門部で学んだ | 漫画の本+Gペン |
| 8位 | 学部生数・女子学生数とも国立大学で最多 | 学生アイコン |
| 7位 | 国立総合大学で唯一の外国語学部(25専攻語) | 地球儀+各国語の吹き出し |
| 6位 | 1931年、6番目の帝国大学として誕生 | 帝国大学の建物 |
| 5位 | 石黒浩教授のアンドロイド研究(大阪・関西万博パビリオン) | 半分メカの顔 |
| 4位 | レーザー科学研究所の大型レーザー(激光XII号、核融合研究) | 12本のビームが1点に集中 |
| 3位 | 2020年、iPS細胞由来の心筋シートを世界で初めて移植 | 心臓+細胞シート |
| 2位 | ルーツは1838年に緒方洪庵が開いた適塾(福沢諭吉らが学ぶ) | 町家+「適塾」ののれん |
| 1位 | 湯川秀樹(大阪帝大で中間子論を発表)、2025年 坂口志文特任教授がノーベル生理学・医学賞 | 金メダル+紙吹雪 |
| まとめ | 10項目の一覧+「コメントで教えてね！」 | |

## 再生成の方法

```bash
cd osaka-univ-top10
python3 narrate.py     # ナレーション合成 → output/narration.wav, output/timeline.js(シーン尺), output/subtitles_ja.srt
node capture.js        # render.html を 1 フレームずつ撮影 → output/video_silent.mp4
python3 mix.py         # BGM(ダッキング)+効果音+ナレーションをミックスし -14 LUFS に正規化 → output/osaka_univ_top10.mp4
./export_upload.sh     # upload/ に最終mp4・SRT・サムネイルを書き出す
```

- `script.py` … 原稿。書き換えて `narrate.py` から順に再実行すれば、シーン尺も字幕も自動で追従します
- `narrate.py` … 文ごとに VOICEVOX で合成し、発話の長さからシーン尺を決定(話速 1.27)。`VOICEVOX_STYLE=0`(あまあま)、`6`(ツンツン)などで声色を変更可能
- `render.html` … Canvas 2D で `render(t)` が時刻 t のフレームを決定論的に描画。ブラウザで開くとプレビュー再生、`?t=秒` で静止
- `capture.js` … Playwright(Chromium)で撮影し ffmpeg(libx264)へ。`node capture.js --stills 10,20` で確認用静止画
- `bgm.py` … 明るいポップ調BGM(Cメジャー、118BPM、F–G–Em–Am)。キック・クラップ・ハイハット・ベース・裏拍スタブ・グロッケン
- `mix.py` … ナレーション中は BGM を自動で下げ(ダッキング)、シーン切替の「シュッ」、順位表示の「キラン」、1位のファンファーレを追加
- フォント: M PLUS Rounded 1c(SIL Open Font License、`fonts/OFL.txt`)

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT` |
| 音声モデル `0.vvm`(四国めたん・ずんだもん 等) | VOICEVOX/voicevox_vvm releases(0.16.2) | `VOICEVOX_VVMS` |
| Open JTalk 辞書 | `pip install pyopenjtalk`(初回に自動ダウンロード) | `VOICEVOX_DICT`(任意) |

既定パスは `/home/user/vv/ort/...` と `/home/user/vv/vvms`。

## クレジット・注意

- 音声を公開する際は VOICEVOX 利用規約により「VOICEVOX:四国めたん」の表記が必要です(動画のまとめ画面と説明文に記載済み)
- 大学のロゴ・写真は使用していません(イラストはすべて Canvas で自作)
- 内容は 2026年11月時点の公開情報にもとづきます。マチカネワニの年代は資料により約42万〜45万年前と幅があります
