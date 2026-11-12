# ランドスケープアーキテクト紹介 — ショート動画

ランドスケープアーキテクトの「なり方・年収・有名な会社と人物」を解説する縦型ショート動画
(1080×1920 / 30fps / 約98秒)。ナレーションは VOICEVOX:四国めたん、BGM は自作(プログラム合成)。

- 完成動画: `output/landscape_architect_short.mp4`
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.jpg`
- ナレーションのみ: `output/narration.wav` / BGM のみ: `output/bgm.wav`

## 構成

| シーン | 内容 |
|---|---|
| タイトル | ランドスケープアーキテクトとは |
| どんな仕事? | 公園・広場・街路・水辺など屋外空間の計画・設計 |
| なり方 | 学ぶ → 就職 → 実務+資格 の3ステップ |
| 主な資格 | 登録ランドスケープアーキテクト(RLA)。指定学科の大卒は実務3年以上。資格は必須ではない |
| 年収の目安 | 日本:設計職の求人で400〜600万円台(概算)/米国:中央値 約8万ドル |
| 有名な会社 | 日建設計、オンサイト計画設計事務所、E-DESIGN / SWA Group、Sasaki、Field Operations |
| 有名な人物 | F・L・オルムステッド、ジェームズ・コーナー、長谷川浩己、忽那裕樹 |
| まとめ | 要点とクレジット |

## 数値の根拠と注意

- RLA の受験要件: ランドスケープコンサルタンツ協会「2024年 RLA資格認定試験 受験の手引き」(学歴により実務3〜12年)。最新年度の手引きで要確認。
- 米国の年収中央値 $79,320: 米労働統計局(BLS)OEWS 2023年5月。
- 造園工の平均 約352万円: 令和6年 賃金構造基本統計調査(求人サイト経由の二次情報で確認)。
- **日本の「400〜600万円台」は公的統計ではなく、設計職の求人を踏まえた概算**です。この職種単独の公的統計はありません。動画内にもその旨を表示しています。

## 再生成

```bash
npm install                 # 表示用フォント(Noto Sans JP)
python3 narrate.py          # ナレーション合成 → output/narration.wav, subtitles_ja.srt, timings.js
node capture.js             # 映像(無音)→ output/video_silent.mp4
python3 mix.py              # BGM をダッキングしてミックス、-14 LUFS に正規化 → 完成 mp4
```

- `script.py` … 原稿(字幕表記と読み上げ表記のペア)。シーンの長さは音声の長さから自動で決まる
- `render.html` … `render(t)` が時刻 t の画面を描く。ブラウザで開くとプレビュー、`?t=30` で静止表示
- `bgm.py` … Cメジャー / 96BPM の軽いBGMを numpy で合成(外部音源なし)
- 必要なもの: Node.js + playwright(Chromium)、ffmpeg、Python 3 + numpy + pyopenjtalk、VOICEVOX CORE 0.17.1
  (wheel・`voicevox_onnxruntime` 1.17.3・音声モデル `0.vvm`。場所は `VOICEVOX_ORT` / `VOICEVOX_VVMS` で指定)

公開時は VOICEVOX の利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要です(動画内に常時表示済み)。
